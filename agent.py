"""TaskPilot core: planner, risk classifier, tools with undo, approval gate."""
import json, os, re, time, uuid, copy, requests

PROVIDERS = {  # all OpenAI-compatible chat-completions endpoints
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "meta-llama/llama-3.3-70b-instruct:free"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "gemini-2.0-flash"),
    "nvidia": ("https://integrate.api.nvidia.com/v1/chat/completions", "meta/llama-3.1-70b-instruct"),
}

# ---------- sandbox workspace (swap these adapters for real Gmail/Calendar/Notion MCP servers) ----------
def fresh_workspace():
    return {
        "calendar": {"e1": {"title": "Dentist appointment", "when": "2026-10-05 10:00"},
                     "e2": {"title": "Team standup", "when": "2026-10-06 09:30"}},
        "inbox": [{"id": "m1", "from": "clinic@smilecare.in", "subject": "Appointment reminder: Dentist, 5 Oct 10:00"}],
        "sent": [],
        "notes": {"n1": {"title": "Todo", "body": "Submit hackathon project"}},
        "forms": [],
    }

# tool name -> (risk reason or None, description)
TOOLS = {
    "calendar.list":        (None, "List calendar events"),
    "calendar.move_event":  (None, "Reschedule an event (args: match, when)"),
    "calendar.create_event":(None, "Create an event (args: title, when)"),
    "calendar.delete_event":("deletes data", "Delete an event (args: match)"),
    "gmail.search":         (None, "Search inbox (args: query)"),
    "gmail.send":           ("sends a message externally", "Send email (args: to, subject, body)"),
    "notion.add_note":      (None, "Add a note (args: title, body)"),
    "notion.delete_note":   ("deletes data", "Delete a note (args: match)"),
    "browser.submit_form":  ("submits a form on a third-party site", "Fill+submit a web form (args: url, fields)"),
}

def _find(d, match):
    m = (match or "").lower()
    for k, v in d.items():
        if m and m in v["title"].lower():
            return k
    return None

def preview(ws, tool, a):
    """Before/after preview shown at the approval gate."""
    if tool == "calendar.delete_event":
        k = _find(ws["calendar"], a.get("match")); return {"before": ws["calendar"].get(k), "after": None}
    if tool == "gmail.send":
        return {"before": None, "after": {"to": a.get("to"), "subject": a.get("subject"), "body": a.get("body")}}
    if tool == "notion.delete_note":
        k = _find(ws["notes"], a.get("match")); return {"before": ws["notes"].get(k), "after": None}
    if tool == "browser.submit_form":
        return {"before": None, "after": {"url": a.get("url"), "fields": a.get("fields")}}
    return {"before": None, "after": a}

def execute(ws, tool, a):
    """Run one step. Returns (result_text, undo_record or None)."""
    if tool == "calendar.list":
        return "; ".join(f'{v["title"]} @ {v["when"]}' for v in ws["calendar"].values()), None
    if tool == "calendar.move_event":
        k = _find(ws["calendar"], a.get("match"))
        if not k: return "No matching event found", None
        old = ws["calendar"][k]["when"]; ws["calendar"][k]["when"] = a["when"]
        return f'Moved "{ws["calendar"][k]["title"]}" {old} -> {a["when"]}', {"op": "set_when", "k": k, "when": old}
    if tool == "calendar.create_event":
        k = "e" + uuid.uuid4().hex[:4]; ws["calendar"][k] = {"title": a["title"], "when": a["when"]}
        return f'Created "{a["title"]}" @ {a["when"]}', {"op": "del_event", "k": k}
    if tool == "calendar.delete_event":
        k = _find(ws["calendar"], a.get("match"))
        if not k: return "No matching event found", None
        ev = ws["calendar"].pop(k); return f'Deleted "{ev["title"]}"', {"op": "restore_event", "k": k, "ev": ev}
    if tool == "gmail.search":
        q = (a.get("query") or "").lower()
        hits = [m["subject"] for m in ws["inbox"] if q in m["subject"].lower() or q in m["from"].lower()]
        return f"{len(hits)} match(es): " + " | ".join(hits), None
    if tool == "gmail.send":
        ws["sent"].append({"to": a["to"], "subject": a["subject"], "body": a["body"]})
        return f'Email sent to {a["to"]}', None  # a sent email cannot be unsent
    if tool == "notion.add_note":
        k = "n" + uuid.uuid4().hex[:4]; ws["notes"][k] = {"title": a["title"], "body": a.get("body", "")}
        return f'Added note "{a["title"]}"', {"op": "del_note", "k": k}
    if tool == "notion.delete_note":
        k = _find(ws["notes"], a.get("match"))
        if not k: return "No matching note found", None
        n = ws["notes"].pop(k); return f'Deleted note "{n["title"]}"', {"op": "restore_note", "k": k, "n": n}
    if tool == "browser.submit_form":
        ws["forms"].append(a); return f'Submitted form at {a.get("url")}', None  # real build: Playwright
    return f"Unknown tool {tool}", None

def undo(ws, u):
    op = u["op"]
    if op == "set_when": ws["calendar"][u["k"]]["when"] = u["when"]
    elif op == "del_event": ws["calendar"].pop(u["k"], None)
    elif op == "restore_event": ws["calendar"][u["k"]] = u["ev"]
    elif op == "del_note": ws["notes"].pop(u["k"], None)
    elif op == "restore_note": ws["notes"][u["k"]] = u["n"]

# ---------- planner ----------
SYSTEM = ("You are TaskPilot's planner. Break the user's request into the fewest steps using ONLY these tools:\n"
          + "\n".join(f"- {k}: {v[1]}" for k, v in TOOLS.items())
          + '\nReturn ONLY JSON: {"steps":[{"tool":"...","args":{...},"why":"..."}]}. Dates as YYYY-MM-DD HH:MM.')

def llm_plan(text):
    prov = os.getenv("LLM_PROVIDER", "groq"); key = os.getenv("LLM_API_KEY")
    if not key or prov not in PROVIDERS: return None
    url, default = PROVIDERS[prov]
    r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=40, json={
        "model": os.getenv("LLM_MODEL", default), "temperature": 0,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]})
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", raw, re.S).group(0))["steps"]

def rule_plan(text):
    """Offline demo planner so the app works with no API key."""
    t = text.lower(); steps = []
    date = re.search(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", text)
    when = date.group(0) if date else "2026-10-12 10:00"
    if "reschedule" in t or "move" in t:
        m = "dentist" if "dentist" in t else ("standup" if "standup" in t else t.split()[-1])
        steps.append({"tool": "calendar.move_event", "args": {"match": m, "when": when}, "why": "Update the calendar"})
        if "email" in t or "tell" in t or "notify" in t or "dentist" in t:
            steps.append({"tool": "gmail.send", "args": {"to": "clinic@smilecare.in", "subject": "Reschedule request",
                          "body": f"Hello, I'd like to move my appointment to {when}. Please confirm."}, "why": "Notify the other party"})
    elif "delete" in t or "cancel" in t:
        steps.append({"tool": "calendar.delete_event", "args": {"match": "standup" if "standup" in t else "dentist"}, "why": "Remove the event"})
    elif "note" in t or "remind" in t:
        steps.append({"tool": "notion.add_note", "args": {"title": text[:40], "body": text}, "why": "Save a note"})
    else:
        steps.append({"tool": "calendar.list", "args": {}, "why": "Show what's on the calendar"})
    return steps

def plan(text):
    try:
        steps = llm_plan(text)
    except Exception:
        steps = None
    src = "llm" if steps else "offline-rules"
    steps = steps or rule_plan(text)
    steps = [s for s in steps if s.get("tool") in TOOLS]
    for s in steps:
        s["risk"] = TOOLS[s["tool"]][0]  # approval gate: derived from tool policy, never from the model
        s["status"] = "pending"
    return steps, src

# ---------- run engine ----------
RUNS, WS, LOG = {}, fresh_workspace(), []

def advance(run):
    """Run steps until a risky one needs approval or the plan finishes."""
    for s in run["steps"]:
        if s["status"] != "pending": continue
        if s["risk"]:
            s["status"] = "awaiting_approval"; s["preview"] = preview(WS, s["tool"], s["args"])
            run["status"] = "awaiting_approval"; return run
        _do(run, s)
    run["status"] = "done"; return run

def _do(run, s):
    res, u = execute(WS, s["tool"], s["args"])
    s["status"], s["result"] = "done", res
    LOG.append({"id": uuid.uuid4().hex[:6], "run": run["id"], "tool": s["tool"], "result": res,
                "approved": bool(s["risk"]), "undo": u, "undone": False, "ts": time.strftime("%H:%M:%S")})

def decide(run, approve):
    s = next(x for x in run["steps"] if x["status"] == "awaiting_approval")
    if approve: _do(run, s)
    else:
        s["status"] = "rejected"
        for x in run["steps"]:
            if x["status"] == "pending": x["status"] = "skipped"
    return advance(run)

def new_run(text):
    steps, src = plan(text)
    run = {"id": uuid.uuid4().hex[:6], "text": text, "planner": src, "steps": steps, "status": "planned"}
    RUNS[run["id"]] = run; return advance(run)
