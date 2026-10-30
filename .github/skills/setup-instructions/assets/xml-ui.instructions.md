---
applyTo: "**/res/layout/**,**/*Fragment.kt,**/navigation/**"
generated-by: copilot-workflow
---

# UI conventions

- Layouts are XML with View Binding. Do not introduce Jetpack Compose or Data Binding, even for a
  small isolated screen — see `architecture.md` for why this app stays on View Binding.
- Every screen Fragment extends the shared `BaseFragment`, not `Fragment` directly.
- Navigation goes through the single `HomeActivity`'s Navigation Component graph. Don't host a new
  `NavHostFragment` elsewhere.
- Arguments between destinations use Safe Args — no manual `Bundle` construction for nav arguments.
- A ViewModel is registered in Koin's `AppModule.kt` (see `koin-di.instructions.md`), not
  instantiated directly in the Fragment.
- Every new screen gets a ViewModel test — see `testing.instructions.md` and the `new-screen`
  project skill.
