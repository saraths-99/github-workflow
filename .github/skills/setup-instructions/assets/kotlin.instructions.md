---
applyTo: "**/*.kt,**/*.kts"
generated-by: copilot-workflow
---

# Kotlin conventions

- Null safety: prefer non-null types; use `?` only at real API/DB/network boundaries, never as a
  substitute for handling a failure case.
- Errors: return `Result<T, E>` (`kotlin-result`) from repository and service functions — see
  `data-layer.instructions.md`. Do not throw for expected failure paths; reserve exceptions for
  programmer errors.
- Coroutines: suspend functions for I/O; inject dispatchers (don't hardcode `Dispatchers.IO`) so
  tests can substitute a test dispatcher — see `testing.instructions.md`.
- No new architectural layers: this app is MVVM + Repository + Services. Don't introduce a
  use-case/interactor layer even if it looks like a natural refactor — see `architecture.md` for why.
- Visibility: keep implementation classes `internal` or private to their module unless another
  module genuinely needs them; check the module map in `copilot-instructions.md` before widening
  visibility across a module boundary.
