---
applyTo: "**/test/**,**/androidTest/**"
---

# Testing conventions

- Use the project's existing coroutine test dispatcher setup and fakes — don't introduce a new
  mocking library or test-dispatcher pattern alongside the existing one.
- A ViewModel, service, repository or Room change is not done until its matching test exists — see
  the `write-tests` project skill and the per-type skills (`new-screen`, `new-api-call`,
  `room-migration`, `new-ble-command`), each of which includes its own test.
- `test-writer` doesn't write tests itself — it routes each task to the matching specialized
  sub-agent (`unit-test-writer`, `ble-protocol-test-writer`, `androidtest-writer`,
  `compatibility-test-writer`, `security-test-writer`, and the plan-only `interop-test-writer`,
  `ota-test-writer`, `performance-test-writer`, `chaos-test-writer`) and waits for all of them.
- BLE command tests use a fake device, never a real Halo lock or GDO unit — see
  `ble-halo.instructions.md` / `ble-gdo.instructions.md`.
- Tests live alongside the existing test folders for that module — don't create a new top-level
  test source set.
- `code-reviewer` checks every acceptance criterion in the ticket's `tasks.md` against the
  tests added, not just against the production code.
