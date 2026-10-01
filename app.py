from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
load_dotenv()
import agent

app = Flask(__name__, static_folder="static")

@app.get("/")
def home(): return send_from_directory("static", "index.html")

@app.post("/api/task")
def task():
    text = (request.json or {}).get("text", "").strip()
    if not text: return jsonify(error="empty task"), 400
    return jsonify(agent.new_run(text))

@app.post("/api/run/<rid>/decision")
def decision(rid):
    run = agent.RUNS.get(rid)
    if not run or run["status"] != "awaiting_approval": return jsonify(error="nothing to approve"), 400
    return jsonify(agent.decide(run, bool((request.json or {}).get("approve"))))

@app.post("/api/undo/<lid>")
def undo(lid):
    e = next((x for x in agent.LOG if x["id"] == lid), None)
    if not e or not e["undo"] or e["undone"]: return jsonify(error="cannot undo"), 400
    agent.undo(agent.WS, e["undo"]); e["undone"] = True
    return jsonify(ok=True)

@app.get("/api/state")
def state():
    log = [{k: v for k, v in e.items() if k != "undo"} | {"undoable": bool(e["undo"]) and not e["undone"]} for e in agent.LOG]
    return jsonify(workspace=agent.WS, log=log[::-1])

@app.post("/api/reset")
def reset():
    agent.WS.clear(); agent.WS.update(agent.fresh_workspace()); agent.LOG.clear(); agent.RUNS.clear()
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
