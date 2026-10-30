---
applyTo: "**/AppModule.kt,**/di/**"
generated-by: copilot-workflow
---

# Dependency injection conventions

- Koin modules live in `AppModule.kt` (or a `di/` package for a larger module) — register new
  ViewModels, repositories and services there, not with manual `by lazy` singletons.
- `GdoSdk` keeps its own manual DI and is intentionally not migrated to Koin — don't try to fold it
  in; see `architecture.md` for why it stays separate.
- Scope new definitions to the narrowest Koin scope that works (`factory` for ViewModels,
  `single` for repositories/services) rather than defaulting everything to `single`.
- When a task spans modules, check the module map in `copilot-instructions.md` for which module's
  `AppModule.kt` should own the new definition — don't duplicate a binding across modules.
