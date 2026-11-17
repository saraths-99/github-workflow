---
mode: agent
model: ['Claude Opus 5.5 (copilot)', 'GPT-6.1 Sol (copilot)', 'GPT-5.6 Sol (copilot)', 'Claude Sonnet 5.5 (copilot)']
description: Start a ticket and carry it through to its PRs — detects bug vs. feature, plans, implements and ships, with every stop a question to pick an answer for. Usage: /qatalyst-ticket-start <ticket ID>
---

Run the `qatalyst-ticket-start` skill for the ticket ID given as an argument:

0. Run `python3 .github/token-tracker/scripts/token_tracker.py mark <ticket ID>` so this chat's
   token usage is linked to the ticket (skip silently if it can't run).
1. Read the ticket's Jira issue type and project key, match the project key against this repo's
   configured `jira_projects`, and compare the issue type against that project's own
   `bug_issue_types`. If it's a bug and `log-analysis.md` doesn't exist yet, hand off to
   `qatalyst-log-analyser` first and wait for it to finish — don't require a separate manual step for
   this.
2. Hand off to `qatalyst-bug-planner` (for a bug) or `qatalyst-feature-planner` (otherwise) — it
   reads the ticket, its Confluence/Figma links and the matching workflow doc, writes to the
   deterministic `specs/<bug|feature>/<ticket ID>/tasks.md` path (same path `qatalyst-log-analyser`
   already used, for a bug). Ask for approval: approve, request changes, or stop.
3. Create the feature branch once `tasks.md` is approved.
4. Ask whether to move the ticket to In Progress.
5. Hand off to `qatalyst-developer` to work every task; if the plan stops fitting, get it updated
   and re-approved.
6. Once every task is ticked, ask whether to ship now; if so, run the `qatalyst-ticket-ship` skill.

If the ticket was started before, resume instead of starting over: an existing draft goes straight
to the approval question, a feature branch or ticked tasks go straight to implementation from the
first unticked task, and all tasks ticked goes straight to the ship question (see the skill's
"Resuming" section).

Every question offers options to pick, per the `qatalyst-ask-developer` skill — never an open-ended
one. If no ticket ID is given, ask for one first, offering the developer's own open Jira tickets.
