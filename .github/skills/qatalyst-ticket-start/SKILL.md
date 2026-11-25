---
name: qatalyst-ticket-start
description: >
  /qatalyst-ticket-start <ticket ID>. The single entry point for any ticket, from any
  of this repo's configured Jira projects, and the one flow that carries it
  through to shipping — detects whether it's a bug from its Jira issue type
  (checked against whichever configured project the ticket actually belongs
  to), hands off to the matching planner (bug-planner, after log-analyser
  runs if it hasn't already, or feature-planner), gets tasks.md approved,
  creates the ticket branch (bug/ or feature/), runs qatalyst-developer through every task,
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

Token tracking runs in VS Code only. Before step 0, check where you are: you're in VS Code if you
have the `vscode/askQuestions` tool (Android Studio's chat has `ask_questions`, the Copilot CLI
`ask_user`).

- **In VS Code**, and you can run terminal commands: run
  `python3 .github/token-tracker/scripts/token_tracker.py mark <ticket ID>`. It only appends a line
  to `.logs/token-tracker/markers.jsonl`, so this chat's model calls can be linked to the ticket
  later. Then tell every agent you hand off to "Token tracking: on".
- **Anywhere else**, or if you can't run commands: do nothing and say nothing. Create no files, and
  tell every agent you hand off to "Token tracking: off".

Never let this step fail or delay the ticket.

## Repowise check

Before step 0, once per run (a resume too), check that Repowise is ready. The app is five
repositories, and Repowise is what lets the planners, the log analyser and the reviewers see a
change's callers in the other repos — without it they read only the files they're pointed at.

1. If you can run terminal commands, run `repowise status --workspace` and read which repos are
   missing or behind. Either way, probe the MCP server with one cheap code-graph call:
   `search_codebase` with a one-word query and `limit` 1. Don't use `get_overview`: it returns the
   generated overview essay, which an index built with `--no-prose` (the one this workflow uses)
   doesn't have, so it comes back unreadable on a healthy index. A "no index" reply means not
   indexed; the tool not being offered, or a timeout, means the MCP server isn't running.
2. **Ready** — it answers, and every repo in `architecture.md`'s repository table is indexed and up
   to date. Say so in one line ("Repowise ready — 5 repos indexed"), then make sure the commit hook
   is in place (below), and carry on.

   **The commit hook.** Repowise can re-index a repo after every commit, which keeps the index
   current through the ticket. If you can run terminal commands, run `repowise hook status
   --workspace` (it only reads). For each repo it reports without the hook: if that repo's
   `.git/hooks/post-commit` already exists, it's someone else's hook, so leave it alone and say so;
   otherwise run `repowise hook install <that repo's path>`. Never add `--security`: it installs a
   pre-commit check that can block commits. Say in one line what happened ("Repowise commit hook
   installed in 3 repos", "already in place", or "left alone in <repo>: it has its own post-commit
   hook"). If a command fails, say so in one line and carry on; this never blocks the ticket. Skip it
   when you can't run commands or the developer chose to continue without Repowise.
3. **Not ready** — say which of these it is, and ask (see `qatalyst-ask-developer`), putting the
   command in the question:
   - not installed (`repowise` isn't found; with no terminal, "not installed or its MCP server isn't
     running"): `uv tool install repowise`
   - installed and indexed (`repowise status --workspace` is fine) but the MCP server isn't answering:
     it is defined in `.mcp.json` as `repowise mcp <folder holding all the repos>`, local, with no API key; if its `command` or folder is still a `<...>` placeholder, that is why it won't start. Start it from VS Code's
     **MCP: List Servers**, or by choosing Android Studio's Local agent (`.github/workflow-guide.md`, "MCP servers")
   - not indexed, or repos missing: from the folder that holds all the repos side by side,
     `repowise init --yes --no-prose --no-editor-setup`
   - indexed but behind: `repowise update --workspace`

   Options: I've set it up — check again · Continue without Repowise · Stop, I'll set it up. (If
   the MCP server is the only problem, "Continue without Repowise" means direct file reads; the
   agents never use the CLI index themselves.)
4. Never run `uv tool install`, `repowise init` or `repowise update` yourself — they write to the
   developer's machine, and `init` without `--no-editor-setup` writes into the repos. The commit
   hook above is the one thing you do install.
5. Tell every agent you hand off to the outcome ("Repowise: ready" or "Repowise: the developer
   chose to continue without it"), so none of them re-checks or re-asks.

## 0. Detect whether this is a bug

`jira_projects` (in `copilot-instructions.md`'s settings block) is a list, one entry per Jira
project this repo's tickets can come from. Each entry has its own `key` and `bug_issue_types`; this
app can still track tickets under more than one Jira project, each with its own issue-type scheme,
so there's no single shared `bug_issue_types` to check against.

**Seed the project first.** The project key is the part of the ticket ID the developer typed before
the dash (`HALOM-14123` → `HALOM`). If `jira_projects` still holds the `<FILL IN` placeholder, or has no
entry for that key, add one before anything else, with `bug_issue_types: [Bug]`: a ticket in a project
the file doesn't know is run as a bug by default anyway, and this records it. Edit only the
`jira_projects` list in `copilot-instructions.md`'s settings block: replace the placeholder entry,
or add the new entry under the existing ones, and leave `base_branch` and everything else as it is.
Say it in one line ("Added Jira project HALOM to copilot-instructions.md, bug types: Bug"). If you
can't edit the file, say that in one line and carry on; the ticket is treated as a bug either way.
Step 1 below then reads the real project key from Jira: if it differs from the key you added,
replace the added entry's key with Jira's, and say so.

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
| `tasks.md`, but no task ticked and no ticket branch (see "Branches" in step 2) | Step 1's approval question, on the existing draft — don't re-plan |
| A ticket branch, or any task ticked, and some tasks unticked | Step 4, from the first unticked task |
| Every task ticked | Step 5, the ship question |

**If the last chat broke midway.** `.logs/<ticket ID>/in-progress.json` exists only while a task
or the ship step is running; a clean finish or a "Stop here" answer removes it. If it's there when
you resume, the last chat stopped partway. Tell the developer so, plainly — which task (number and
title) or that it was shipping, when it started, and how many files have uncommitted changes on the
ticket branch — then ask:

- **A task:** continue task N, keeping its changes · restart task N (its uncommitted changes are
  stashed first, as `<ticket ID> task N partial`) · stop here. On "continue", start
  `qatalyst-developer` with "continue task N, keeping its changes".
- **Shipping:** continue shipping · stop here. `qatalyst-ticket-ship` checks which repos already
  have a pushed branch or an open PR and doesn't repeat those.

Before step 4 or 5, switch to the ticket's branch if you're not on it. If the ticket is a bug and
the only branch for it is an old `feature/<ticket ID>-*`, don't switch to it: step 2 says what to do
instead. If git refuses
because of uncommitted changes, ask: stash them and switch, or stop. Ask step 3's In Progress
question only if the ticket isn't In Progress or further along already. Say in one line which step
you're resuming from and why (for example, "3 of 7 tasks ticked — continuing with task 4").

## 1. Planning and approval

Wait for the planner you handed off to (`qatalyst-bug-planner` or `qatalyst-feature-planner`) to
finish: it reads the ticket itself plus its Confluence/Figma links and writes the draft to the
deterministic `specs/<bug|feature>/<ticket ID>/tasks.md` path (see
`qatalyst-spec-folder-resolution` — the same path `qatalyst-log-analyser` already used, for a bug).

Then show the draft and ask for approval: approve, request changes, or stop. In the same call, ask
whether to write tests (**Write tests** or **No tests for this ticket**; see `qatalyst-ask-developer`)
and, if the draft lists two candidate root causes, which to fix. On "No tests", run the planner
again with "apply: no tests" so it records `**Tests:** none` and removes the test parts (see
`qatalyst-plan-ticket`'s Gate); that is the developer's answer applied, so don't ask for approval a
second time for it. On "request changes", run the planner again with the developer's text and ask
again, without the tests question. Don't start step 2 until it's approved.

## 2. Branches

Once `tasks.md` is approved, create the ticket branch: `bug/<ticket ID>-<slug>` when step 0 settled
on a bug (including its default), `feature/<ticket ID>-<slug>` for a feature — the same
`bug`/`feature` word as the spec folder, never a `feature/` branch for a bug.

**The ticket's branch is the one whose prefix matches its type** (`bug/` for a bug, `feature/` for a
feature), with the ticket ID after it. A bug's old `feature/<ticket ID>-*` branch (from before
0.4.6, or created by hand) is not its branch: never switch to it, commit to it or push it. If a
ticket branch already exists, use it and skip the question below.

**Ask which branch to create it from.** Never assume `base_branch`. Ask (see
`qatalyst-ask-developer`) with these options, leaving out any that don't apply:

- `base_branch` (from `copilot-instructions.md`'s settings block), first, as the recommended one.
- The branch the developer is on now, named, if it isn't `base_branch`.
- The tip of the bug's old `feature/<ticket ID>-*` branch, if it has commits beyond `base_branch`
  (say so: that work comes with the new branch, and the `feature/` branch itself stays untouched).
- Another branch (**needs text**: its name).

Create the new branch from the one they pick; if it exists only on the remote, from its remote
copy. If the name they give doesn't exist, say so and ask again. Say in one line which branch was
created from which, and, for a bug with an old `feature/` branch, that the `feature/` branch was
left alone.

Keep the slug short: lowercase kebab-case from the ticket summary, at most 3 words and 25
characters, dropping filler words (the, a, to, when, on, fix, issue). Cut at a word boundary, never
mid-word. `HALOM-123 Lock keeps retrying when the app is backgrounded` becomes
`bug/HALOM-123-lock-retry-background`, not the whole summary. Where the ticket ID alone already says
enough, omit the slug: `bug/HALOM-123`.

## 3. Transition

Ask whether to move the Jira ticket to In Progress — don't transition it silently.

## 4. Implementation

Hand off to `qatalyst-developer` to work `tasks.md` from its first unticked task. If it stops
because the plan doesn't fit the code, have the planner that wrote `tasks.md` update it, ask the
developer to approve the update, then run `qatalyst-developer` again. If it stops because it is
stuck (see its "When you're stuck"), tell the developer plainly what it was doing and what failed,
ask the stuck question from `qatalyst-ask-developer`, and act on the answer: "try again" runs it
again with "continue task N, keeping its changes, and try a different approach"; "I'll look at it"
waits for them, then runs it with "continue task N, keeping its changes"; "restart" stashes the
task's changes (as `<ticket ID> task N partial`) and runs it on task N afresh; "stop here" ends the
flow, and `/qatalyst-ticket-start` resumes from the first unticked task. When it reports every task
ticked (and has shown the token report), show the developer the workflow report in chat, in full,
under its full path (`<repo root>/.logs/<ticket ID>/workflow-report.md`), taking the text from the
agent's reply, or from the file if the reply lacks it. If neither has it, say the report is missing
and why, if known. This is the report's only guaranteed place in every IDE, Android Studio included,
where the token report doesn't run. Then go on to step 5.

## 5. Ship

Every time `qatalyst-developer` reports all tasks ticked (a re-run after a plan update counts, so
does the first), ask two questions in one call: whether to ship now, and whether the developer has
an idea for improving the workflow itself, so the way they'd do it could be adopted (see
`qatalyst-ask-developer`). Deal with the idea first: on "I have an idea", append a line to
`.logs/<ticket ID>/workflow-ideas.md` (git-ignored; create it if it isn't there) holding the UTC
date, the ticket ID and their words as typed, then tell them the file's full path and that it stays
on their machine, so it needs passing to whoever maintains this workflow repo. Don't act on the idea
yourself, change any workflow file because of it, or send it anywhere. On "No idea", say nothing and
create no file. Then the ship answer: on "ship it now", write `.logs/<ticket ID>/in-progress.json` as
`{"step": "ship", "startedAt": "<UTC time>"}`, run the `qatalyst-ticket-ship` skill (which asks its
own questions before pushing), and delete the file when it finishes or is cancelled. On "stop here", say that `/qatalyst-ticket-ship` picks it up later.
Resuming at "every task ticked" goes to the ship question alone: the idea question was asked when the
tasks finished.

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
- Never create the ticket branch before `tasks.md` is approved.
- Never move the Jira ticket's status without asking first.
- Never ask an open-ended question — every stop is one of `qatalyst-ask-developer`'s questions.
