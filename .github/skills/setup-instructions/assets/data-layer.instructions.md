---
applyTo: "**/services/**,**/repository/**,**/datasource/**"
generated-by: copilot-workflow
---

# Data layer conventions

- Services hold business logic; repositories coordinate data sources; there is no use-case layer —
  see `architecture.md`.
- Every repository/service function that can fail returns `Result<T, ModuleError>`
  (`kotlin-result`), not a thrown exception.
- Network and database models are mapped to domain models explicitly — don't leak a Retrofit DTO or
  a Room entity past the repository boundary.
- Local storage goes through Room with SQLCipher; tokens and keys are only ever stored encrypted,
  never in `SharedPreferences` or plain files — see the `protect-secrets` hook, which also blocks
  reads/edits of `local.properties` and keystore files.
- A new API call or Room change gets a mocked/migration test — see the `new-api-call` and
  `room-migration` project skills and `testing.instructions.md`.
