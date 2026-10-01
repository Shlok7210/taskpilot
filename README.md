# TaskPilot — plans and runs your everyday app tasks, pausing before anything risky

**Team Xploitme** · BFW/HACK 26 AI Build Challenge · **PS-01 Autonomous Agents for Everyday Apps**
Shlok Gupta · Ishan Jaiswal · Nisha Khadka (Alliance University)

Type one plain-English task ("reschedule my dentist appointment to 2026-10-12 11:00 and email the clinic").
TaskPilot turns it into a step plan, runs the safe steps itself, and **stops at an approval gate** before any step that
sends a message externally, deletes data, spends money or submits a form — showing a before/after preview.
Everything it does lands in an action log with one-tap undo where the action can be reversed.

## How it works
1. **Planner** (`agent.py: plan`) — an LLM (Groq / OpenRouter / Gemini / NVIDIA NIM, all via one OpenAI-compatible call)
   decomposes the request into tool calls. With no API key, an offline rule planner keeps the demo working.
2. **Approval gate** — risk is decided by a fixed **tool policy table** (`TOOLS`), *not* by the model, so a prompt-injected or
   hallucinated plan cannot skip the gate.
3. **Executor** — runs steps in order; safe steps run immediately, risky steps wait for Approve / Reject. Reject skips the rest.
4. **Action log + undo** — each reversible action stores its inverse (move event, create/delete event or note).
   Sent emails and submitted forms are marked *not reversible*.

## Honest scope
The default build runs against a **sandbox workspace** (calendar, inbox, notes) so anyone can try it with no OAuth.
`execute()` is the single adapter point for the real Gmail / Google Calendar / Notion MCP servers and Playwright —
the planner, gate, log and undo do not change when you swap it in.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env        # optional: add a free key (console.groq.com/keys, aistudio.google.com/apikey, openrouter.ai)
python app.py               # http://localhost:5000
python -c "import tests.test_agent as t; [ (t.setup_function(None), getattr(t,n)()) for n in dir(t) if n.startswith('test_')]"
```
(with pytest installed: `pytest -q`)

## Deploy (free)
Push to GitHub → Render/Railway → "New Web Service" from the repo (`render.yaml` / `Procfile` included).
Set `LLM_PROVIDER` and `LLM_API_KEY` as environment variables. Never commit `.env`.
Note: state is in memory (one demo workspace per server process) — fine for a demo, not multi-user.
