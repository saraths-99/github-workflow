---
name: qatalyst-ticket-start
description: >
  /qatalyst-ticket-start <ticket ID>. The single entry point for any ticket, from any
  of this repo's configured Jira projects, and the one flow that carries it
  through to shipping — detects whether it's a bug from its Jira issue type
  (checked against whichever configured project the ticket actually belongs
  to), hands off to the matching planner (bug-planner, after log-analyser
  runs if it hasn't already, or feature-planner), gets tasks.md approved,
  creates the feature branch, runs qatalyst-developer through every task,
  then runs qatalyst-ticket-ship. Every stop is a question with options.
---

# qatalyst-ticket-start

Run at the start of every ticket — this is the only command a developer needs to remember,
regardless of whether the ticket turns out to be a bug or a feature. You decide that yourself, in
step 0, rather than relying on the developer to know and to run `/log-analyser` separately first.
From there the ticket runs as one flow to its PRs: the developer never has to type a command or an
answer to move it on.

You detect the ticket type and hand off — you never write `log-analysis.md` or `tasks.md` yourself;
that's `qatalyst-log-analyser`, `qatalyst-bug-planner` and `qatalyst-feature-planner`. In
particular, you never ask about the spec folder — it's computed deterministically as
`specs/<bug|feature>/<ticket ID>/` from the ticket type you just detected, so there's nothing for
any agent to ask about.

## Asking the developer

Every stop below is a question with options, asked the way `qatalyst-ask-developer` says, with the
options its table lists. When a sub-agent you started returns a question instead of a result, ask
it yourself and run that sub-agent again with the answer.

If no ticket ID was given, ask for one first (the developer's own open tickets as options).

## Token tracking

Before step 0, if you can run terminal commands, run
`python3 .github/token-tracker/scripts/token_tracker.py mark <ticket ID>`. It only appends a line to
`.logs/token-tracker/markers.jsonl`, so this chat's model calls can be linked to the ticket later.
If you can't run commands, skip it without comment: the report still links this chat once one of
its turns runs on the ticket's feature branch. Never let this step fail or delay the ticket.

## 0. Detect whether this is a bug

`jira_projects` (in `copilot-instructions.md`'s settings block) is a list, one entry per Jira
project this repo's tickets can come from. Each entry has its own `key` and `bug_issue_types`; this
app can still track tickets under more than one Jira project, each with its own issue-type scheme,
so there's no single shared `bug_issue_types` to check against.

1. Read the ticket's Jira `issuetype` field **and its project key** via `qatalyst-jira-ticket-intake` —
   never parsed from the ticket ID string.
2. Match that project key against `jira_projects`. If none matches, or the matched entry's
   `bug_issue_types` is empty, there's no bug type to compare against, so **the ticket is treated as
   a bug** — this workflow is mainly run on bugs, so that's the default. Don't ask the developer,
   and don't fall back to another entry's `bug_issue_types`. Say in one line that it's being run as
   a bug and why (project key not in `jira_projects`, or no `bug_issue_types` set for it), then
   carry on.
3. Otherwise compare the ticket's `issuetype` against *that matched project's* `bug_issue_types`.
   Either way, check **Resuming** below before going on — if this ticket was started before, it says
   which step to pick up from instead of 0.4.
4. **If it matches a bug type, or step 2 defaulted it to a bug:**
   - If `specs/bug/<ticket ID>/log-analysis.md` already exists, hand off straight to
     `qatalyst-bug-planner` — it's already been analyzed (via a manual `/log-analyser` run, or a
     previous pass of this same step).
   - Otherwise, hand off to the `qatalyst-log-analyser` agent yourself, exactly as
     `/log-analyser <ticket ID>` would, wait for it to write `log-analysis.md`, then hand off to
     `qatalyst-bug-planner`.
5. **If the matched project's `bug_issue_types` doesn't include the ticket's type**, hand off
   straight to `qatalyst-feature-planner`.

A developer can still run `/log-analyser <ticket ID>` manually and ahead of time if they want to
look at the logs before deciding to start the ticket at all — in that case step 0.4's "already
exists" branch just picks it up.

## Resuming

A chat can break partway through a ticket, or the developer can stop at a question and come back.
Running `/qatalyst-ticket-start` again picks up where the ticket is, worked out from what's on disk
— never by asking the developer which step they were on. With the spec folder known from step 0:

| What's there | Pick up at |
|---|---|
| No `tasks.md` | Step 0.4, as normal |
| `tasks.md`, but no task ticked and no `feature/<ticket ID>-*` branch | Step 1's approval question, on the existing draft — don't re-plan |
| A `feature/<ticket ID>-*` branch, or any task ticked, and some tasks unticked | Step 4, from the first unticked task |
| Every task ticked | Step 5, the ship question |

**If the last chat broke midway.** `.logs/<ticket ID>/in-progress.json` exists only while a task
or the ship step is running; a clean finish or a "Stop here" answer removes it. If it's there when
you resume, the last chat stopped partway. Tell the developer so, plainly — which task (number and
title) or that it was shipping, when it started, and how many files have uncommitted changes on the
feature branch — then ask:

- **A task:** continue task N, keeping its changes · restart task N (its uncommitted changes are
  stashed first, as `<ticket ID> task N partial`) · stop here. On "continue", start
  `qatalyst-developer` with "continue task N, keeping its changes".
- **Shipping:** continue shipping · stop here. `qatalyst-ticket-ship` checks which repos already
  have a pushed branch or an open PR and doesn't repeat those.

Before step 4 or 5, switch to the ticket's feature branch if you're not on it. If git refuses
because of uncommitted changes, ask: stash them and switch, or stop. Ask step 3's In Progress
question only if the ticket isn't In Progress or further along already. Say in one line which step
you're resuming from and why (for example, "3 of 7 tasks ticked — continuing with task 4").

## 1. Planning and approval

Wait for the planner you handed off to (`qatalyst-bug-planner` or `qatalyst-feature-planner`) to
finish: it reads the ticket itself plus its Confluence/Figma links and writes the draft to the
deterministic `specs/<bug|feature>/<ticket ID>/tasks.md` path (see
`qatalyst-spec-folder-resolution` — the same path `qatalyst-log-analyser` already used, for a bug).

Then show the draft and ask for approval: approve, request changes, or stop. If the draft lists two
candidate root causes, ask which to fix in the same question set. On "request changes", run the
planner again with the developer's text and ask again. Don't start step 2 until it's approved.

## 2. Branches

Once `tasks.md` is approved, create `feature/<ticket ID>-<slug>`, branched from `base_branch` (in
`copilot-instructions.md`'s settings block).

## 3. Transition

Ask whether to move the Jira ticket to In Progress — don't transition it silently.

## 4. Implementation

Hand off to `qatalyst-developer` to work `tasks.md` from its first unticked task. If it stops
because the plan doesn't fit the code, have the planner that wrote `tasks.md` update it, ask the
developer to approve the update, then run `qatalyst-developer` again. When it reports every task
ticked (and has shown the token report), go on to step 5.

## 5. Ship

Ask whether to ship now. On "ship it now", write `.logs/<ticket ID>/in-progress.json` as
`{"step": "ship", "startedAt": "<UTC time>"}`, run the `qatalyst-ticket-ship` skill (which asks its
own questions before pushing), and delete the file when it finishes or is cancelled. On "stop here", say that `/qatalyst-ticket-ship` picks it up later.

## Sizing

A one-line fix still goes through this flow, just with a short `tasks.md` and a single task — don't
skip the approval gate, and don't skip step 0's detection, even for a small ticket.

## Rules

- Never guess at the ticket's type from its title or description — step 0 reads the actual Jira
  `issuetype` field; a title that happens to contain the word "bug" is not the signal.
- Never write to `log-analysis.md` or `tasks.md` yourself — only `qatalyst-log-analyser`,
  `qatalyst-bug-planner` and `qatalyst-feature-planner` do, and only inside
  `specs/<bug|feature>/<ticket ID>/`.
- Never ask about the spec folder yourself, or let a planner ask — the path is deterministic from
  the ticket type and ID, so it's never asked about at all.
- Never create a feature branch before `tasks.md` is approved.
- Never move the Jira ticket's status without asking first.
- Never ask an open-ended question — every stop is one of `qatalyst-ask-developer`'s questions.
