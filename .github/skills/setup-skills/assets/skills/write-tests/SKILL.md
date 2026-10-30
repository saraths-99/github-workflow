---
name: write-tests
description: >
  The project's test patterns: coroutine test dispatchers and the existing
  fakes, in the existing test folders. Used directly for a task that is
  test-only, or as the shared convention the narrower skills' test steps
  follow.
generated-by: copilot-workflow
---

# write-tests

Used by `test-writer` for any test, and directly by `developer` for a task that's test-only (e.g.
closing a coverage gap `code-reviewer` flagged).

## Conventions

- Use the project's existing coroutine test dispatcher setup — don't add a second one alongside it.
- Use the existing fakes for BLE devices, network responses, and Room — don't add a new mocking
  library if an existing fake already covers the case.
- Tests live in the existing `test/` or `androidTest/` folder for the module being tested, matching
  the existing package structure — never a new top-level test source set (see
  `testing.instructions.md`).
- A test asserts against the acceptance criteria in the ticket's `requirements.md` it's meant to
  satisfy, not just "the code runs without throwing."

## Per-area pointers

- ViewModel/screen tests — see `new-screen`.
- BLE command tests (fake device, never a real lock/GDO unit) — see `new-ble-command`.
- API call tests (mocked network, never a real endpoint) — see `new-api-call`.
- Room migration tests (run the real `Migration` against the previous schema) — see
  `room-migration`.
