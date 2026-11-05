---
name: ticket-start
description: >
  /ticket-start <ticket ID>. The single entry point for any ticket, from any
  of this repo's configured Jira projects — detects whether it's a bug from
  its Jira issue type (checked against whichever configured project the
  ticket actually belongs to) and hands off to the matching planner:
  bug-planner (after log-analyser runs, if it hasn't already) or
  feature-planner. Once that planner's tasks.md is approved, creates the
  feature branch and asks before moving the ticket to In Progress.
---

# ticket-start

Run at the start of every ticket — this is the only command a developer needs to remember,
regardless of whether the ticket turns out to be a bug or a feature. You decide that yourself, in
step 0, rather than relying on the developer to know and to run `/log-analyser` separately first.

You detect the ticket type and hand off — you never write `log-analysis.md` or `tasks.md` yourself;
that's `log-analyser`, `bug-planner` and `feature-planner`. In particular, you never ask about the
feature folder — whichever planner you hand off to resolves that itself.

## 0. Detect whether this is a bug

`jira_projects` (in `copilot-instructions.md`'s settings block) is a list, one entry per Jira
project this repo's tickets can come from. Each entry has its own `key` and `bug_issue_types`; this
app can still track tickets under more than one Jira project, each with its own issue-type scheme,
so there's no single shared `bug_issue_types` to check against.

1. Read the ticket's Jira `issuetype` field **and its project key** via Atlassian Rovo MCP — read
   the project key from the ticket's own Jira data, never parsed from the ticket ID string.
2. Match that project key against `jira_projects`. If none matches, **stop and ask the
   developer** — this is a ticket from a Jira project this repo hasn't been configured for; don't
   guess which entry's `bug_issue_types` to fall back to.
3. Compare the ticket's `issuetype` against *that matched project's* `bug_issue_types`.
4. **If it matches a bug type:**
   - If `specs/<feature>/<ticket ID>/log-analysis.md` already exists, hand off straight to
     `bug-planner` — it's already been analyzed (via a manual `/log-analyser` run, or a previous
     pass of this same step).
   - Otherwise, hand off to the `log-analyser` agent yourself, exactly as `/log-analyser <ticket ID>`
     would, wait for it to write `log-analysis.md`, then hand off to `bug-planner`.
5. **If it doesn't match a bug type**, hand off straight to `feature-planner`.

A developer can still run `/log-analyser <ticket ID>` manually and ahead of time if they want to
look at the logs before deciding to start the ticket at all — in that case step 0.4's "already
exists" branch just picks it up.

## 1. Planning

Wait for the planner you handed off to (`bug-planner` or `feature-planner`) to finish: it reads the
ticket itself plus its Confluence/Figma links, resolves the feature folder (reusing
`log-analyser`'s, for a bug), and produces one `tasks.md`, approved by the developer. Don't start
the next step until that approval has happened.

## 2. Branches

Once `tasks.md` is approved, create `feature/<ticket ID>-<slug>`, branched from `base_branch` (in
`copilot-instructions.md`'s settings block).

## 3. Transition

Ask the developer before moving the Jira ticket to In Progress — don't transition it silently.

## Sizing

A one-line fix still goes through this flow, just with a short `tasks.md` and a single task — don't
skip the approval gate, and don't skip step 0's detection, even for a small ticket.

## Rules

- Never guess at the ticket's type from its title or description — step 0 reads the actual Jira
  `issuetype` field; a title that happens to contain the word "bug" is not the signal.
- Never write to `log-analysis.md` or `tasks.md` yourself — only `log-analyser`, `bug-planner` and
  `feature-planner` do, and only inside `specs/<feature>/<ticket ID>/`.
- Never ask about the feature folder yourself — that's the planner's job, so it's asked at most
  once per ticket.
- Never create a feature branch before `tasks.md` is approved.
- Never move the Jira ticket's status without asking first.
- If a ticket's project key doesn't match any entry in `jira_projects`, or the matched entry's
  `bug_issue_types` is empty, stop and ask the developer — don't silently treat it as a feature or
  borrow another project's `bug_issue_types` as a fallback.
