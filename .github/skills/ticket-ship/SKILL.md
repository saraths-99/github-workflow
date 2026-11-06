---
name: ticket-ship
description: >
  /ticket-ship. Checks every task is ticked, runs code-reviewer and
  security-reviewer/error-handling-reviewer where flagged, plus the local
  build and tests, then asks once and commits, pushes and opens the
  Bitbucket PR. Checks the Pipelines run where Pipelines is on, and moves
  the ticket to In Review.
---

# ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then ship — you don't implement anything
yourself.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't ship a
   partial ticket.
2. Run `code-reviewer` against the full diff; run `security-reviewer` too if `code-reviewer` flagged
   a sensitive area, and `error-handling-reviewer` too if it flagged a layer where functions can
   fail. All must pass with no open comments.
3. Build and run tests locally with `isLocalBuild=true`.
4. **Ask the developer once**, showing: the files that will be pushed, and the PR title and
   description. Do nothing in steps 5–7 until they say yes.
5. Commit, push `feature/<ticket ID>-<slug>`, and open the Bitbucket PR. The spec folder
   (`specs/<feature>/<ticket ID>/`) ships in the same PR.
6. Check whether Bitbucket Pipelines is on (see `pipelines-detection.md`'s three-step check). Where
   it's on, wait for the PR's Pipelines run to pass. Where it's off, say so in the PR description
   instead of waiting for a check that won't appear.
7. Once the gate clears, move the Jira ticket to In Review.

## If the Bitbucket tools aren't available

Push the branch anyway, then print the PR title and description for the developer to paste into
Bitbucket by hand — don't block the whole ship step on one missing tool.

## Rules

- Never push or open a PR before the single confirmation in step 4.
- Never report a Pipelines check as passing without actually reading the run (Rovo MCP's
  pipeline-runs tool for the PR's source commit, falling back to the REST `pullrequests/{id}/statuses`
  endpoint).
- Never move the ticket to In Review until the gate has cleared.
