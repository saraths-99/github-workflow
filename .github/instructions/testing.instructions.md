---
applyTo: "**/test/**,**/androidTest/**"
---

# Testing conventions

- **Check for existing coverage before writing anything.** Use Repowise (or a direct search, if
  unavailable or unreachable) to find whether a test already exercises the exact behavior being
  changed.
  - Already covered and still accurate → write nothing new; report that coverage already exists,
    naming the test, rather than adding a duplicate.
  - Already covered but now stale (the change altered the behavior it asserts) → update that test
    in place. A stale assertion that still happens to pass is worse than no test at all.
  - Not covered → write a new test.
- Use the project's existing coroutine test dispatcher setup and fakes — don't introduce a new
  mocking library or test-dispatcher pattern alongside the existing one.
- A ViewModel, service, repository or Room change is not done until its matching test exists.
  `test-writer` doesn't write tests itself — it routes each task to the matching specialized
  sub-agent (`unit-test-writer`, `ble-protocol-test-writer`, `androidtest-writer`,
  `compatibility-test-writer`, `security-test-writer`, and the plan-only `interop-test-writer`,
  `ota-test-writer`, `performance-test-writer`, `chaos-test-writer`) and waits for all of them. A
  standalone test-only task outside any ticket reaches the same routing via `/write-tests`.
- Per-area detail: ViewModel/screen tests — see `new-screen`; BLE command tests (fake device, never
  a real Halo lock or GDO unit) — see `new-ble-command`, `ble-halo.instructions.md` /
  `ble-gdo.instructions.md`; API call tests (mocked network, never a real endpoint) — see
  `new-api-call`; Room migration tests (run the real `Migration` against the previous schema) —
  see `room-migration`.
- Tests live alongside the existing test folders for that module — don't create a new top-level
  test source set.
- `code-reviewer` checks every acceptance criterion in the ticket's `tasks.md` against the
  tests added, not just against the production code.
