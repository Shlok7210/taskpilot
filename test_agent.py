import agent

def setup_function(_):
    agent.WS.clear(); agent.WS.update(agent.fresh_workspace()); agent.LOG.clear(); agent.RUNS.clear()

def test_reschedule_then_gate_on_email_and_undo():
    run = agent.new_run("Reschedule my dentist appointment to 2026-10-12 11:00 and email the clinic")
    assert agent.WS["calendar"]["e1"]["when"] == "2026-10-12 11:00"      # safe step ran
    assert run["status"] == "awaiting_approval" and not agent.WS["sent"]  # email held at the gate
    assert run["steps"][1]["preview"]["after"]["to"] == "clinic@smilecare.in"
    agent.decide(run, True)
    assert len(agent.WS["sent"]) == 1 and run["status"] == "done"
    agent.undo(agent.WS, agent.LOG[0]["undo"])
    assert agent.WS["calendar"]["e1"]["when"] == "2026-10-05 10:00"

def test_reject_skips_and_changes_nothing():
    run = agent.new_run("Delete my team standup")
    assert run["status"] == "awaiting_approval" and "e2" in agent.WS["calendar"]
    agent.decide(run, False)
    assert "e2" in agent.WS["calendar"] and run["steps"][0]["status"] == "rejected"

def test_risk_comes_from_policy_not_model():
    steps, _ = agent.plan("Delete my team standup")
    assert steps[0]["risk"] == "deletes data"
