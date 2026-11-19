---
mode: agent
model: ['Claude Opus 5.5 (copilot)', 'GPT-6.1 Sol (copilot)', 'GPT-5.6 Sol (copilot)', 'Claude Sonnet 5.5 (copilot)']
description: Ship a finished ticket — review, build, one PR per repo in merge order. Usage: /qatalyst-ticket-ship
---

Run the `qatalyst-ticket-ship` skill:

1. Confirm every `tasks.md` task is ticked (`qatalyst-developer` already checked its own diff
   against `tasks.md`).
2. Run the local build/tests.
3. Show the planned PRs and merge order, and ask once before pushing anything: push and open the
   PRs, or cancel.
4. On confirmation, push and open one cross-linked PR per repo, in merge order.
5. Per repo, loop up to 5 passes: wait on Pipelines (where it's on) and Rovo's PR Code Reviewer;
   hand any open comments to `qatalyst-developer` to fix, push, and re-check. After 5 passes with
   comments still open, ask the developer whether to keep iterating.
6. Move the ticket to In Review once every repo's gate clears.
