---
name: qatalyst-new-screen
description: >
  Adds a screen — a Jetpack Compose screen for a new one, or the Fragment and
  XML layout (View Binding, extending BaseFragment) for a change to an
  existing XML screen — with a ViewModel registered in AppModule.kt, a nav
  destination, and a ViewModel test.
---

# qatalyst-new-screen

Used by `qatalyst-developer` (directly, or via `qatalyst-new-feature`) for a task that adds or changes one
screen.

## Steps

1. Decide which kind of task this is. A **new** screen is built in Compose; a change to an
   **existing** screen stays in its XML layout — don't convert it to Compose unless the task says to
   (see `xml-ui.instructions.md`).
2. **New screen:** add it in Compose, hosted and wired the way the existing Compose screens in the app
   are — read one first with `qatalyst-repowise-lookup`. If there is no existing Compose screen to
   follow, or Compose isn't enabled in the app's build, stop and report it as a plan mismatch; don't
   change build config or invent a hosting pattern.
   **Existing screen:** change its Fragment (extending the shared `BaseFragment` — never `Fragment`
   directly) and its XML layout under `res/layout/` with View Binding — no Data Binding.
3. Add the ViewModel and register it using the `qatalyst-koin-wiring` skill.
4. Add the nav destination to the existing graph hosted by `HomeActivity`, with Safe Args for any
   arguments — no manual `Bundle` construction.
5. Hand off to `qatalyst-test-writer` for the ViewModel test, using the project's existing test
   dispatcher
   and fakes (see `testing.instructions.md`).

## Done means

The screen is reachable from the existing nav graph, the ViewModel is Koin-registered, and its test
passes locally — not just that the screen compiles.
