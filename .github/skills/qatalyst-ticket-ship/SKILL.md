---
name: qatalyst-ticket-ship
description: >
  /qatalyst-ticket-ship. Checks every task is ticked (qatalyst-developer
  already checked its own diff against tasks.md), plus the local build and
  tests, then asks once and commits, pushes, and opens one cross-linked
  Bitbucket PR per repo touched, in merge order. Waits on each repo's
  Pipelines run, and loops Rovo's PR Code Reviewer's comments back through
  qatalyst-developer until each repo's PR is clean, before moving the
  ticket to In Review.
---

# qatalyst-ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then ship — you don't implement anything
yourself. A ticket's diff can span more than one repo (see `architecture.md`'s module/repo map) —
treat every step below as per-repo unless it says otherwise.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't ship a
   partial ticket. There's no separate review step here: `qatalyst-developer` already checked the
   diff against `tasks.md` and the specs-only rule itself before reporting every task ticked.
2. Build and run tests locally with `isLocalBuild=true`, in every repo touched. Where a module's
   build ignores test failures (see `testing.instructions.md`), read its test report instead of
   trusting the exit code.
3. **Ask the developer once**, showing: the planned PRs and their merge order (which repo depends on
   which), the files that will be pushed in each, and each PR's title and description. Ask with
   options, per `qatalyst-ask-developer`: push and open the PRs, or cancel. Do nothing in steps 4–6
   until they pick "push".
4. On confirmation, commit, push `feature/<ticket ID>-<slug>` in each repo, and open one
   cross-linked Bitbucket PR per repo, in merge order. When continuing a ship that a broken chat
   left partway, check each repo first and skip the push or PR it already has. The spec folder
   (`specs/<bug|feature>/<ticket ID>/`) ships in whichever repo owns it (see `architecture.md`'s
   module map) — never duplicated across repos.
5. Per repo, **the Rovo review loop** — up to 5 passes:
   1. Check whether Bitbucket Pipelines is on (see `pipelines-detection.md`'s three-step check).
      Where it's on, wait for that repo's PR's Pipelines run; note a failure, but don't let it block
      checking Rovo's review too — fix both kinds of problem together in one pass. Where it's off,
      say so in that PR's description instead of waiting for a check that won't appear.
   2. Wait for Rovo's PR Code Reviewer to finish on this repo's PR (Rovo MCP's review-status tool
      for the PR, if available; otherwise poll the PR's comments).
   3. If it raised no open comments and Pipelines passed (or is off), this repo's gate is clear —
      stop the loop for this repo.
   4. Otherwise, hand `qatalyst-developer` every open comment Rovo raised (file, line, comment text)
      — see its "Addressing Rovo PR Code Reviewer comments" section. Once it reports back, commit
      and push the fix to the same branch, then repeat from 5.1.
   5. After 5 passes with comments still open, stop and ask the developer, per `qatalyst-ask-
      developer`: keep iterating, or stop here and resolve the rest by hand. On "stop here", leave
      this repo's PR as-is and don't move the ticket to In Review until it clears some other way.
6. Once every repo's gate clears, move the Jira ticket to In Review.

## If the Bitbucket tools aren't available

Push every branch anyway, then print each repo's PR title and description for the developer to
paste into Bitbucket by hand — don't block the whole ship step on one missing tool.

## Rules

- Never push or open any PR before the single confirmation in step 3 — one confirmation covers every
  repo, not one ask per repo.
- Never report a repo's Pipelines check as passing without actually reading that repo's run (Rovo
  MCP's pipeline-runs tool for that PR's source commit, falling back to the REST
  `pullrequests/{id}/statuses` endpoint). Same for Rovo's PR Code Reviewer — read its actual review
  state, never assume it passed because enough time went by.
- Never move the ticket to In Review until every repo's gate has cleared — one repo passing doesn't
  clear the others, and a repo stopped at step 5.5 hasn't cleared either.
