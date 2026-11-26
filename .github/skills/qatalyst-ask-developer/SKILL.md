---
name: qatalyst-ask-developer
description: >
  How every agent and skill in this workflow asks the developer anything —
  always as a question with options to pick, never an open-ended prompt the
  developer has to type an answer to. Shared by every step that stops for
  the developer.
---

# qatalyst-ask-developer

This workflow runs as one flow from `/qatalyst-ticket-start` to the shipped PR. Wherever it stops
for the developer, the developer answers by picking an option, not by typing. This skill is how.

## Asking

1. Ask with whichever question tool you have: `vscode/askQuestions` in VS Code, `ask_questions` in
   Android Studio's Copilot chat, `ask_user` in the Copilot CLI. One short question, and 2–4
   options. Put the safe or recommended option first.
2. Each option is a complete answer that tells you exactly what to do next ("Skip log analysis",
   not "Yes"). Never offer an option that then needs a typed follow-up, except the ones marked
   below as needing text.
3. Several independent questions at the same stop go in one `askQuestions` call, not one after
   another.
4. Where none of these tools is available, write the same question with numbered options and
   accept the number alone as the answer.
5. Never end a turn with an open-ended question such as "What would you like to do?" or "Let me
   know how to proceed." If you need the developer, it's one of the questions below or a new one in
   the same shape.

## When you're running as a sub-agent

A sub-agent may not be able to ask the developer itself. If you can't, stop and return the question
and its options to the agent that started you, word for word, as your result. That agent asks it
and runs you again with the answer.

## Where the workflow stops, and the options to offer

| Stop | Options |
|---|---|
| No ticket ID given | The developer's own open Jira tickets (`assignee = currentUser() AND statusCategory != Done`, newest first, up to 4: "`ABC-123` — summary"). The tool's free-text answer is the only way to give another ID. |
| Repowise isn't ready at ticket start (say which: not installed · not indexed · repos missing or behind, naming them · MCP server not running — with the command or step to fix it) | I've set it up — check again · Continue without Repowise · Stop, I'll set it up |
| Bug ticket has no log attachment | UI-only issue — skip log analysis · I've attached it now — check again · Stop, I'll attach it later |
| Bug ticket has a log but no issue time | I'll give the time (**needs text**: `HH:MM:SS`, plus the date if the log spans days) · Use the whole log, no time window · Stop, I'll add the time to the ticket |
| Raw log isn't in `.logs/<ticket ID>/raw/` and the download from the ticket couldn't run or failed (say why, and the exact folder and file name to save it as) | I've saved it there — continue · Skip log analysis |
| Review comments still open after 3 rounds (show them, with the reviewer and file) | I'll fix it by hand, then check again · Ship anyway, comments open · Cancel |
| Digest has no warnings or errors (the window has lines, but nothing to analyse) | Widen the time window · Use the whole log · The log shows nothing for this issue — report it as inconclusive · Wrong attachment — stop |
| Trimmed log came out nearly empty | Widen the time window · Use the whole log · Wrong attachment — stop |
| `log-analysis.md` has two candidate root causes | Fix cause A (name it) · Fix cause B (name it) · Fix both |
| The planner's fix check found the fix is already in the code, is blocked (platform, permission, policy or other limit), or is too ambiguous to choose (say which, with the evidence) | Do not produce a fix · Go with a fix anyway |
| `tasks.md` draft ready, the first time it is shown (two questions, one call) | **Plan:** Approve · Request changes (**needs text**: what to change) · Stop here. **Tests:** Write tests (recommended) · No tests for this ticket |
| `tasks.md` draft shown again (after changes or a plan update) | Approve · Request changes (**needs text**: what to change) · Stop here. The tests question is not asked again; the draft's `Tests:` line stands |
| Plan doesn't fit the code mid-task (updated `tasks.md`) | Approve the updated plan · Stop here |
| Creating the ticket branch (after `tasks.md` is approved, and no ticket branch exists yet) | `base_branch`, named (recommended) · The branch you're on now, named (only if it isn't `base_branch`) · The tip of the old `feature/<ticket ID>-*` branch (bugs only, only if it has commits beyond `base_branch`) · Another branch (**needs text**: its name) |
| Move the ticket to In Progress | Move to In Progress · Leave it where it is |
| Resuming, but uncommitted changes block switching to the ticket branch | Stash them and switch · Stop here |
| Resuming after the last chat broke partway through task N (say so first) | Continue task N, keeping its changes · Restart task N (stash its changes first) · Stop here |
| Resuming after the last chat broke partway through shipping (say so first) | Continue shipping · Stop here |
| Every task ticked (two questions, one call) | **Ship:** Ship it now · Stop here, I'll ship later. **Idea:** I have an idea for the workflow (**needs text**: describe it) · No idea, nothing to add |
| `qatalyst-developer` is stuck on a task (say which task, what it was doing, what failed and how many times, or which command has gone quiet and for how long) | Try again, a different approach · I'll look at it, then continue the task · Restart task N (stash its changes first) · Stop here |
| A build, test run or Pipelines run is stuck at ship (say which, and for how long it has been quiet) | Keep waiting · I'll look at it, then continue shipping · Stop here |
| Which tests to run before pushing (ship step 5, after the build) | Unit tests in every module touched (recommended) · All tests: unit, then instrumented (needs an emulator or device) · Only this ticket's tests · Skip tests (build only; the PRs say tests weren't run) |
| The commit title and message are shown (at ship, and when the developer stops to ship later) | Use this message · Make it shorter · Add more detail · Change it (**needs text**: what to change) |
| Push and open the PRs | Push and open the PRs · Cancel |

Approving a terminal command or tool call (Allow / Allow all) is Copilot's own prompt, not a
question you ask.
