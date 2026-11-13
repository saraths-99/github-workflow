---
name: qatalyst-ticket-start
description: >
  /qatalyst-ticket-start <ticket ID>. The single entry point for any ticket, from any
  of this repo's configured Jira projects — detects whether it's a bug from
  its Jira issue type (checked against whichever configured project the
  ticket actually belongs to) and hands off to the matching planner:
  bug-planner (after log-analyser runs, if it hasn't already) or
  feature-planner. Once that planner's tasks.md is approved, creates the
  feature branch and asks before moving the ticket to In Progress.
---

# qatalyst-ticket-start

Run at the start of every ticket — this is the only command a developer needs to remember,
regardless of whether the ticket turns out to be a bug or a feature. You decide that yourself, in
step 0, rather than relying on the developer to know and to run `/log-analyser` separately first.

You detect the ticket type and hand off — you never write `log-analysis.md` or `tasks.md` yourself;
that's `qatalyst-log-analyser`, `qatalyst-bug-planner` and `qatalyst-feature-planner`. In
particular, you never ask about the spec folder — it's computed deterministically as
`specs/<bug|feature>/<ticket ID>/` from the ticket type you just detected, so there's nothing for
any agent to ask about.

## 0. Detect whether this is a bug

`jira_projects` (in `copilot-instructions.md`'s settings block) is a list, one entry per Jira
project this repo's tickets can come from. Each entry has its own `key` and `bug_issue_types`; this
app can still track tickets under more than one Jira project, each with its own issue-type scheme,
so there's no single shared `bug_issue_types` to check against.

1. Read the ticket's Jira `issuetype` field **and its project key** via `qatalyst-jira-ticket-intake` —
   never parsed from the ticket ID string.
2. Match that project key against `jira_projects`. If none matches, **stop and ask the
   developer** — this is a ticket from a Jira project this repo hasn't been configured for; don't
   guess which entry's `bug_issue_types` to fall back to.
3. Compare the ticket's `issuetype` against *that matched project's* `bug_issue_types`.
4. **If it matches a bug type:**
   - If `specs/bug/<ticket ID>/log-analysis.md` already exists, hand off straight to
     `qatalyst-bug-planner` — it's already been analyzed (via a manual `/log-analyser` run, or a
     previous
     pass of this same step).
   - Otherwise, hand off to the `qatalyst-log-analyser` agent yourself, exactly as
     `/log-analyser <ticket ID>`
     would, wait for it to write `log-analysis.md`, then hand off to `qatalyst-bug-planner`.
5. **If it doesn't match a bug type**, hand off straight to `qatalyst-feature-planner`.

A developer can still run `/log-analyser <ticket ID>` manually and ahead of time if they want to
look at the logs before deciding to start the ticket at all — in that case step 0.4's "already
exists" branch just picks it up.

## 1. Planning

Wait for the planner you handed off to (`qatalyst-bug-planner` or `qatalyst-feature-planner`) to
finish: it reads the ticket itself plus its Confluence/Figma links, writes to the deterministic
`specs/<bug|feature>/<ticket ID>/tasks.md` path (see `qatalyst-spec-folder-resolution` — the same path
`qatalyst-log-analyser` already used, for a bug), and produces one `tasks.md`, approved by the
developer. Don't start the next step until that approval has happened.

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
- Never write to `log-analysis.md` or `tasks.md` yourself — only `qatalyst-log-analyser`,
  `qatalyst-bug-planner` and
  `qatalyst-feature-planner` do, and only inside `specs/<bug|feature>/<ticket ID>/`.
- Never ask about the spec folder yourself, or let a planner ask — the path is deterministic from
  the ticket type and ID, so it's never asked about at all.
- Never create a feature branch before `tasks.md` is approved.
- Never move the Jira ticket's status without asking first.
- If a ticket's project key doesn't match any entry in `jira_projects`, or the matched entry's
  `bug_issue_types` is empty, stop and ask the developer — don't silently treat it as a feature or
  borrow another project's `bug_issue_types` as a fallback.
