# Field sources

Reference for filling in [`project-context.md`](../project-context.md) and
[`architecture.md`](../architecture.md) by hand: what counts as solid evidence for each field, and
where to look. A field not listed here follows the general rule in those files' own templates —
cite it if you can, mark it inferred if you're not sure, write `TBD` if you have nothing.

## `project-context.md` fields

| Field | Solid evidence | Inferred-only evidence |
|---|---|---|
| App purpose / domain | An App Store/Play Store listing, a top-level README, or a Confluence page linked from the ticket workflow docs | The app's package name and main feature modules' names |
| Target platforms | `minSdk`/`targetSdk` in `build.gradle.kts`; presence of a `wear/` or `tv/` module | — |
| Core features | Top-level nav graph destinations; feature module names | Fragment/Activity class names alone |
| Users / personas | An explicit note from a developer | Never infer this from code — always `TBD` if not given |
| Integrations (3rd-party SDKs) | A dependency in `libs.versions.toml` with a recognizable vendor name (Nordic BLE, AWS AppSync, etc.) | A transitive dependency pulled in by another library |
| Business constraints (e.g. offline-first, encrypted storage required) | A direct code pattern enforcing it (SQLCipher factory, a lint rule, a CI check) | A comment or doc string mentioning the constraint without enforcement |

## `architecture.md` fields

| Field | Solid evidence | Inferred-only evidence |
|---|---|---|
| Layering | Distinct `*/services/`, `*/repository/`, `*ViewModel.kt` present across multiple features | Only one or two features follow the pattern |
| UI approach | `viewBinding` build flag + XML layouts, with no Compose dependency anywhere | Compose present in one module only — note as a deviation, don't average it away |
| Navigation | Single host Activity + `NavHostFragment` + Safe Args plugin | Multiple Activities each hosting their own nav graph — note as a deviation |
| DI | `koin-android` + `AppModule.kt` definitions covering most feature modules | A module with hand-built singletons alongside Koin elsewhere |
| Module graph | `settings.gradle.kts` `include(...)` calls, read directly — this is a fact, not an inference | — (there is no "inferred" version of a module list) |
| Error handling | `kotlin-result` used in the majority of repository/service return types | A mix of `Result<T,E>` and thrown exceptions — note both, flag the inconsistency |
| Storage | Room `@Database` + a `SupportFactory`/SQLCipher call in the same module | Room without a visible encryption call — note "Room present, encryption not confirmed" |
| BLE stacks | Two distinct top-level packages, each with their own GATT/queue classes, matching Halo vs. GDO naming | Only one BLE package found |
| Known risks / tech debt | An explicit TODO/FIXME convention, a linked Jira epic, or a developer note | Do not infer tech debt from code smell alone — ask, don't guess |
