---
name: write-tests
description: >
  /write-tests. Entry point for a standalone test-only task outside the
  ticket flow (e.g. closing a coverage gap code-reviewer flagged). Hands
  off to test-writer, which routes it to the matching sub-agent(s) exactly
  as it does for a task inside tasks.md.
---

# write-tests

Used directly by a developer for a test-only task that isn't part of an in-progress ticket's
`tasks.md`. You don't write anything yourself and you don't decide which sub-agent applies — hand
off to `test-writer` with a description of the code to test, the same way `developer` does for a
task inside a ticket. `test-writer` runs its routing table either way, so a standalone task and a
ticket task reach the same sub-agents through the same path.

See `testing.instructions.md` for the project's test conventions (existing-coverage check,
dispatcher/fakes reuse, folder location, per-area pointers) — every sub-agent `test-writer` might
route to already follows those, so this skill adds nothing on top.
