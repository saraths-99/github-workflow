---
mode: agent
description: Ship a finished ticket — review, build, one PR per repo in merge order. Usage: /ticket-ship
generated-by: copilot-workflow
---

Run the `ticket-ship` skill:

1. Confirm every `tasks.md` task is ticked.
2. Run `code-reviewer` (and `security-reviewer` if flagged) and the local build/tests.
3. Show the planned PRs and merge order, and ask once before pushing anything.
4. On confirmation, push and open one cross-linked PR per repo, in merge order.
5. Check each repo's Pipelines run where Pipelines is on; note it in the PR description where it's
   off.
6. Move the ticket to In Review once every repo's gate clears.
