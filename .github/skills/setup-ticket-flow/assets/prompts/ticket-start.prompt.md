---
mode: agent
description: Start a ticket — auto-detects bug vs. feature, then Requirements/Design/Tasks. Usage: /ticket-start <ticket ID>
generated-by: copilot-workflow
---

Run the `ticket-start` skill for the ticket ID given as an argument:

1. Read the ticket's Jira issue type and project key, match the project key against this repo's
   configured `jira_projects`, and compare the issue type against that project's own
   `bug_issue_types`. If it's a bug and `log-analysis.md` doesn't exist yet, hand off to
   `log-analyser` first and wait for it to finish — don't require a separate manual step for this.
2. Read the ticket, its Confluence/Figma links, and the matching workflow doc.
3. Ask which feature this belongs to (listing existing `specs/*/` folders), or reuse the
   log-analyser's feature folder if one was already set.
4. Hand off to `ticket-analyst` for `requirements.md`, then `architect` for `design.md` and
   `tasks.md` — wait for approval after each.
5. Create the feature branches once `tasks.md` is approved.
6. Ask before moving the ticket to In Progress.

If no ticket ID is given, ask for one before doing anything else.
