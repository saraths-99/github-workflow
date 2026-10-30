---
name: ticket-ship
description: >
  /ticket-ship. Checks every task is ticked, runs code-reviewer and
  security-reviewer plus the local build and tests, then asks once and
  commits, pushes and opens one Bitbucket PR per repo in merge order,
  cross-linked. Checks each repo's Pipelines run where Pipelines is on, and
  moves the ticket to In Review.
base_branch: <BASE_BRANCH>
repos: <REPO_LIST>
merge_order: <MERGE_ORDER>
generated-by: copilot-workflow
---

# ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then ship — you don't implement anything
yourself.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't ship a
   partial ticket.
2. Run `code-reviewer` against the full diff; run `security-reviewer` too if `code-reviewer` flagged
   a sensitive area. Both must pass with no open comments.
3. Build and run tests locally with `isLocalBuild=true`, for every repo touched.
4. **Ask the developer once**, showing: the repos and files that will be pushed, the PR title and
   description for each repo, and the merge order (`<MERGE_ORDER>`). Do nothing in steps 5–7 until
   they say yes.
5. Commit, push `feature/<ticket ID>-<slug>` in each touched repo, and open one Bitbucket PR per
   repo, cross-linked to each other, in merge order (`<MERGE_ORDER>` — SDK/library repos before the
   app repo). The spec folder (`specs/<feature>/<ticket ID>/`) ships in the app repo's own PR.
6. For each repo, check whether Bitbucket Pipelines is on (see
   `setup-ticket-flow/references/pipelines-detection.md`'s three-step check). Where it's on, wait
   for that PR's Pipelines run to pass. Where it's off, say so in that PR's description instead of
   waiting for a check that won't appear.
7. Once every repo's gate clears, move the Jira ticket to In Review.

## If the Bitbucket tools aren't available

Push the branch anyway, then print the PR title and description for the developer to paste into
Bitbucket by hand — don't block the whole ship step on one missing tool.

## Rules

- Never push or open a PR before the single confirmation in step 4.
- Never report a Pipelines check as passing without actually reading the run (Rovo MCP's
  pipeline-runs tool for the PR's source commit, falling back to the REST `pullrequests/{id}/statuses`
  endpoint).
- Never move the ticket to In Review until every repo's own gate has cleared.
