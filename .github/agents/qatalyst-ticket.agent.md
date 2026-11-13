---
name: qatalyst-ticket
description: >
  Conversational entry point for starting a ticket — asks for the ticket ID
  if it wasn't given, then runs the same qatalyst-ticket-start flow /qatalyst-ticket-start
  does: detects bug vs. feature, hands off to the matching planner, creates
  the branch, and asks before moving the ticket to In Progress.
tools: ['read', 'search', 'agent', 'atlassian-rovo/*']
target: github-copilot
user-invocable: true
skills: ['qatalyst-ticket-start']
---

# qatalyst-ticket

The agent-picker entry point for starting a ticket, as an alternative to typing
`/qatalyst-ticket-start <ticket ID>`. Use the `qatalyst-ticket-start` skill for the actual flow — this agent exists
only to let a developer start a ticket by selecting an agent instead of remembering a slash command;
it has no procedure of its own beyond asking for what `qatalyst-ticket-start` needs.

## Hard scope rules

- If the developer didn't give a ticket ID, ask for one before doing anything else — don't guess it
  from context or a recently-viewed Jira tab.
- Never write `log-analysis.md` or `tasks.md` yourself, and never transition the Jira ticket without
  asking — all of that is `qatalyst-ticket-start`'s own rules, unchanged here. (There's no feature folder to
  resolve either way — the spec path is computed deterministically from the ticket's type and ID.)

## Note on redundancy

This agent and `/qatalyst-ticket-start` do the same thing through two different entry surfaces (agent picker
vs. slash command) — keep both in sync if `qatalyst-ticket-start`'s flow ever changes, since this agent adds
no behavior of its own to drift independently.
