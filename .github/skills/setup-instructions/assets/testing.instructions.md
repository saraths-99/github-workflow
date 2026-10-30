---
applyTo: "**/test/**,**/androidTest/**"
generated-by: copilot-workflow
---

# Testing conventions

- Use the project's existing coroutine test dispatcher setup and fakes — don't introduce a new
  mocking library or test-dispatcher pattern alongside the existing one.
- A ViewModel, service, repository or Room change is not done until its matching test exists — see
  the `write-tests` project skill and the per-type skills (`new-screen`, `new-api-call`,
  `room-migration`, `new-ble-command`), each of which includes its own test.
- BLE command tests use a fake device, never a real Halo lock or GDO unit — see
  `ble-halo.instructions.md` / `ble-gdo.instructions.md`.
- Tests live alongside the existing test folders for that module — don't create a new top-level
  test source set.
- `code-reviewer` checks every acceptance criterion in the ticket's `requirements.md` against the
  tests added, not just against the production code.
