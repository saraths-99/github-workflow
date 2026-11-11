---
mode: agent
description: Start a ticket — auto-detects bug vs. feature, then hands off to the matching planner. Usage: /ticket-start <ticket ID>
---

Run the `ticket-start` skill for the ticket ID given as an argument:

1. Read the ticket's Jira issue type and project key, match the project key against this repo's
   configured `jira_projects`, and compare the issue type against that project's own
   `bug_issue_types`. If it's a bug and `log-analysis.md` doesn't exist yet, hand off to
   `qatalyst-log-analyser` first and wait for it to finish — don't require a separate manual step for
   this.
2. Hand off to `qatalyst-bug-planner` (for a bug) or `qatalyst-feature-planner` (otherwise) — it
   reads the ticket, its
   Confluence/Figma links and the matching workflow doc, resolves the feature folder itself
   (reusing `qatalyst-log-analyser`'s for a bug), and produces one approved `tasks.md`. Wait for
   approval.
3. Create the feature branch once `tasks.md` is approved.
4. Ask before moving the ticket to In Progress.

If no ticket ID is given, ask for one before doing anything else.
