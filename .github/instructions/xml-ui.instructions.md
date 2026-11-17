---
applyTo: "**/res/layout/**,**/*Fragment.kt,**/navigation/**,**/compose/**"
---

# UI conventions

- Existing screens are XML layouts with View Binding; newer screens are built with Jetpack Compose.
  A new screen is a Compose screen. A change to an existing screen stays in its XML layout — don't
  convert it to Compose unless the ticket asks for that. Never introduce Data Binding. See
  `architecture.md`'s UI section.
- A new Compose screen follows how the app's existing Compose screens (the `compose/` package) are
  hosted and wired — read one first. If there is none to follow, or the app's build doesn't have
  Compose enabled, don't edit build config or invent a hosting pattern: report it back as a plan
  mismatch.
- Every XML screen Fragment extends the shared `BaseFragment`, not `Fragment` directly.
- Navigation goes through the single `HomeActivity`'s Navigation Component graph. Don't host a new
  `NavHostFragment` elsewhere.
- Arguments between destinations in that graph use Safe Args — no manual `Bundle` construction for nav
  arguments.
- A ViewModel is registered in Koin's `AppModule.kt` (see `koin-di.instructions.md`), not
  instantiated directly in the Fragment or the composable.
- Every new screen gets a ViewModel test — see `testing.instructions.md` and the `qatalyst-new-screen`
  project skill.
