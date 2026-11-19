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
  `qatalyst-test-writer` doesn't write tests itself — it routes each task to the matching
  specialized
  sub-agent (`qatalyst-unit-test-writer`, `qatalyst-ble-protocol-test-writer`, `qatalyst-androidtest-writer`,
  `qatalyst-compatibility-test-writer`, `qatalyst-security-test-writer`, and the plan-only `qatalyst-interop-test-writer`,
  `qatalyst-ota-test-writer`, `qatalyst-performance-test-writer`, `qatalyst-chaos-test-writer`) and waits for all of them. A
  standalone test-only task outside any ticket reaches the same routing via `/qatalyst-write-tests`.
- Per-area detail: ViewModel/screen tests — see `qatalyst-new-screen`; BLE command tests (fake device, never
  a real Halo lock or GDO unit) — see `qatalyst-new-ble-command`, `ble-halo.instructions.md` /
  `ble-gdo.instructions.md`; API call tests (mocked network, never a real endpoint) — see
  `qatalyst-new-api-call`; Room migration tests (run the real `Migration` against the previous schema) —
  see `qatalyst-room-migration`.
- Tests live alongside the existing test folders for that module — don't create a new top-level
  test source set.
- **Edge cases.** For every function the change adds or alters, ask: empty or null input; a limit or
  boundary value; the same call twice (is it safe to repeat?); cancelled or interrupted partway; the
  process restarted mid-way; another caller of the same code. Cover the ones that can happen, and
  every item in the ticket's `tasks.md` Edge cases section; say which you left out and why.
- **A bug gets a regression test.** The first acceptance criterion's test reproduces the reported
  scenario. When the production change is small, confirm the test fails without it: temporarily
  revert only the production files (`git stash push -- <those paths>`), run the test, restore them
  (`git stash pop`) and check `git status` that they're back. Say whether you saw it fail; never claim
  it did without running it.
- **A green Gradle task is not a passing test run** where a module's build ignores test failures
  (`architecture.md`'s Testing conventions names them): read that module's test report for failures.
- `qatalyst-developer` checks every acceptance criterion and every edge case in the ticket's
  `tasks.md` against the tests added, not just against the production code, once every task is
  ticked.
