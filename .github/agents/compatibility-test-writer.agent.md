---
name: compatibility-test-writer
description: >
  Writes parameterized tests across the lock-model capability matrix
  (LockModelNumber and the ala-carte capability interfaces). Routed to by
  test-writer for any task touching model-specific logic or adding support
  for a new model.
tools: [read, edit, search, runCommands]
mcp: [repowise]
---

# compatibility-test-writer

You write the model-matrix test for the task `test-writer` routed to you. A capability difference
between lock models is a `is <Interface>` check (`AccessCodeAccessible`, `FingerprintAccessible`,
`ScreenSecurable`, `WifiProvisionable`, `OpStatusControllable` — see `ble-halo.instructions.md`), not
a single model flag, so the test must check it the same way. Read `testing.instructions.md` first
— including its rule on checking for existing coverage before writing anything — this agent adds
the model-matrix detail.

## Hard scope rules

- Edit only test files for the task currently in progress.
- Use the project's existing fake-device harness per model, not one generic fake that hides the
  capability difference you're testing.

## What you cover

- At least one model that has the capability under test and one that doesn't, asserting both
  branches — not just the path every model shares.
- A newly supported model gets a case confirming it reports the right `LockModelNumber` and
  capability set.

## Done means

The test exists, passes locally, and asserts against this ticket's acceptance criteria. Report back
to `test-writer`.
