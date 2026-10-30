# Pipelines detection

`ticket-ship` must not assume Bitbucket Pipelines exists for a repo. For each repo in the ticket's
merge order, check in this exact order and stop at the first signal that answers the question:

1. **The repo's `pipelines_config` setting**, read via Atlassian Rovo MCP (or the Bitbucket REST
   API if Rovo MCP doesn't expose it) — this is the authoritative, direct answer: Pipelines is
   explicitly on or off.
2. **Any existing pipeline run** for the repo — if Pipelines has ever run, it's on, regardless of
   what the config setting currently reads (a run already happened).
3. **A `bitbucket-pipelines.yml` file in the repo** — the weakest signal. Its presence suggests
   Pipelines *could* run, but does not prove it's enabled; never treat this file alone as
   confirmation.

## What `ticket-ship` does with the answer, per repo

- **Pipelines on** — the PR's Pipelines run must pass before this repo's part of the ticket can move
  toward In Review. Read the run via Rovo MCP's pipeline-runs tool for the PR's source commit; if
  that's not reliable, fall back to Bitbucket's REST `pullrequests/{id}/statuses` endpoint (Rovo MCP
  has no dedicated tool for a PR's commit statuses).
- **Pipelines off** — skip the check for this repo; the gate is the local build and tests from the
  Verify phase instead. Say so explicitly in that repo's PR description — "no pipeline ran for this
  repo" — so a reviewer doesn't go looking for a CI check that was never going to appear.

## Ticket-level gate

The ticket only moves to In Review once every repo's gate (Pipelines pass, or local build+tests for
a repo with Pipelines off) has cleared — a repo with Pipelines on can't be waived just because
another repo in the same ticket has it off.
