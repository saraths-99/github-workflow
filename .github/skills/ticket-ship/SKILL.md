---
name: ticket-ship
description: >
  /ticket-ship. Checks every task is ticked, runs code-reviewer and
  security-reviewer/error-handling-reviewer where flagged, plus the local
  build and tests, then asks once and commits, pushes, and opens one
  cross-linked Bitbucket PR per repo touched, in merge order. Checks each
  repo's Pipelines run where Pipelines is on, and moves the ticket to In
  Review once every repo's gate clears.
---

# ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then ship — you don't implement anything
yourself. A ticket's diff can span more than one repo (see `architecture.md`'s module/repo map) —
treat every step below as per-repo unless it says otherwise.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't ship a
   partial ticket.
2. Run `qatalyst-code-reviewer` against the full diff in every repo touched; run
   `qatalyst-security-reviewer` too if `qatalyst-code-reviewer` flagged a sensitive area, and
   `qatalyst-error-handling-reviewer` too if it flagged a layer where functions can fail. All must
   pass with no open comments, in every repo.
3. Build and run tests locally with `isLocalBuild=true`, in every repo touched.
4. **Ask the developer once**, showing: the planned PRs and their merge order (which repo depends on
   which), the files that will be pushed in each, and each PR's title and description. Do nothing in
   steps 5–7 until they say yes.
5. On confirmation, commit, push `feature/<ticket ID>-<slug>` in each repo, and open one
   cross-linked Bitbucket PR per repo, in merge order. The spec folder
   (`specs/<bug|feature>/<ticket ID>/`) ships in whichever repo owns it (see `architecture.md`'s
   module map) — never duplicated across repos.
6. Check whether Bitbucket Pipelines is on for each repo (see `pipelines-detection.md`'s three-step
   check, run independently per repo). Where it's on, wait for that repo's PR's Pipelines run to
   pass. Where it's off, say so in that PR's description instead of waiting for a check that won't
   appear.
7. Once every repo's gate clears, move the Jira ticket to In Review.

## If the Bitbucket tools aren't available

Push every branch anyway, then print each repo's PR title and description for the developer to
paste into Bitbucket by hand — don't block the whole ship step on one missing tool.

## Rules

- Never push or open any PR before the single confirmation in step 4 — one confirmation covers every
  repo, not one ask per repo.
- Never report a repo's Pipelines check as passing without actually reading that repo's run (Rovo
  MCP's pipeline-runs tool for that PR's source commit, falling back to the REST
  `pullrequests/{id}/statuses` endpoint).
- Never move the ticket to In Review until every repo's gate has cleared — one repo passing doesn't
  clear the others.
