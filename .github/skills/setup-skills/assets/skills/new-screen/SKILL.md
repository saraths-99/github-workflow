---
name: new-screen
description: >
  Adds a Fragment extending BaseFragment, an XML layout with View Binding, a
  ViewModel registered in AppModule.kt, a nav destination with Safe Args,
  and a ViewModel test.
generated-by: copilot-workflow
---

# new-screen

Used by `developer` (directly, or via `new-feature`) for a task that adds or changes one screen.

## Steps

1. Add the Fragment, extending the shared `BaseFragment` — never `Fragment` directly (see
   `xml-ui.instructions.md`).
2. Add its XML layout under `res/layout/` with View Binding — no Compose, no Data Binding.
3. Add the ViewModel and register it in that module's Koin `AppModule.kt` (see
   `koin-di.instructions.md`), scoped `factory`.
4. Add the nav destination to the existing graph hosted by `HomeActivity`, with Safe Args for any
   arguments — no manual `Bundle` construction.
5. Hand off to `test-writer` for the ViewModel test, using the project's existing test dispatcher
   and fakes (see `testing.instructions.md`).

## Done means

The screen is reachable from the existing nav graph, the ViewModel is Koin-registered, and its test
passes locally — not just that the Fragment compiles.
