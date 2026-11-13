---
name: qatalyst-jira-ticket-intake
description: >
  Reads a Jira ticket in full via Atlassian Rovo MCP — title, description,
  and every comment, not just the description — the shared first step
  behind qatalyst-plan-ticket, qatalyst-log-ticket-intake, and qatalyst-ticket-start's own bug
  detection.
---

# qatalyst-jira-ticket-intake

Used by `qatalyst-bug-planner`, `qatalyst-feature-planner` (via `qatalyst-plan-ticket`), and
`qatalyst-log-ticket-intake` as the common first step of reading a ticket.

## Steps

1. Read the ticket's `issuetype` field and **project key** via Atlassian Rovo MCP — read the project
   key from the ticket's own Jira data, never parsed from the ticket ID string.
2. Read the full ticket text: the description **and every comment**, not just the description.
   Testers and reporters often add the detail that actually matters — an issue time, a repro step,
   a linked design — in a comment rather than the description, so never stop at the first relevant-
   looking text.
3. Note any linked Confluence pages and Figma designs for the caller to fetch separately.

## Done means

The caller has the ticket's project key, issue type, and full text — without re-reading the ticket
a second time later in its own flow. `qatalyst-log-ticket-intake` pins an issue time on top of this as its
own next step; that's not part of this skill.
