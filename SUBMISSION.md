# Final submission — copy/paste kit

## Project title
TaskPilot — an everyday-apps agent that pauses before anything risky

## Project description (+ why we created it)
TaskPilot turns one plain-English request into a plan and carries it out across your apps. Safe steps run on their own;
any step that sends a message, deletes data, spends money or submits a form stops at an approval gate with a before/after
preview. Every action is written to a log, with one-tap undo wherever the action can be reversed.

We built it because rescheduling one appointment means juggling 4–5 apps, which costs students, freelancers and early-career
professionals hours every week — and today's autonomous agents are hard to trust with real accounts. TaskPilot's answer is
that trust comes from design: the risk policy is a fixed table the model cannot override, nothing risky runs unseen, and
mistakes can be undone. Same problem statement as our idea submission: PS-01 Autonomous Agents for Everyday Apps.

## Links
- GitHub repository: <PASTE after you push>
- Deployed link: <PASTE after you deploy on Render/Railway>
- Demo video: <PASTE YouTube/Drive link>
- PPT: TaskPilot_Final_Submission.pptx

## Demo video script (about 2 minutes, screen-record the deployed app)
1. 0:00 — "Rescheduling one appointment means 4–5 apps. We built TaskPilot." Show the empty UI.
2. 0:15 — Click **Reschedule + email**. Point out the plan: 2 steps, planner name shown.
3. 0:35 — Step 1 (calendar) runs by itself; the sandbox panel shows the new time.
4. 0:50 — Step 2 stops: "needs approval: sends a message externally". Show the before/after preview.
5. 1:05 — Click **Approve**; the email appears in the log.
6. 1:20 — Click **Undo** on the calendar move; the event returns to its old time. Note the email is marked not reversible.
7. 1:35 — Run **Delete standup**, click **Reject**; show that nothing was deleted.
8. 1:50 — "Risk is a policy table, not the model's opinion. Swap the adapter for Gmail/Calendar/Notion MCP and Playwright." End on team name.
