# Detection map

Which path instruction blueprint gets written, and the exact signal it's gated on. These reuse the
signals `setup-workflow` already gathered (see `setup-workflow/references/detection-rules.md`) — this
skill does not re-scan the code itself.

| Blueprint | Signal required | Source of the signal |
|---|---|---|
| `kotlin.instructions.md` | None — written unconditionally once any `.kt`/`.kts` file exists in the repo | File extension scan, step 1 |
| `xml-ui.instructions.md` | `viewBinding` build flag or XML under `res/layout/`, and no Compose-only module | "UI toolkit" row, detection-rules.md |
| `koin-di.instructions.md` | `koin-android` dependency + an `AppModule.kt` | "DI" row, detection-rules.md |
| `ble-halo.instructions.md` | A BLE package matching the Halo naming convention (see architecture.md's BLE section once drafted, or the developer's own naming if different) | "BLE stacks" row, detection-rules.md |
| `ble-gdo.instructions.md` | A BLE package matching the GDO naming convention | "BLE stacks" row, detection-rules.md |
| `data-layer.instructions.md` | `*/repository/` or `*/services/` package present | "Layering" row, detection-rules.md |
| `testing.instructions.md` | None — written unconditionally; every supported repo has a `test/` or `androidTest/` source set | — |
| `gradle.instructions.md` | None — written unconditionally; every supported repo builds with Gradle | — |

## When a signal is ambiguous

If a signal is only partially present (e.g. Koin in some modules, manual DI in others — see
`architecture.md`'s "Known risks / deviations" section once drafted), still write the instruction
file, but add one line at the top naming the modules where it doesn't apply, pointing at
`architecture.md` for the detail. Don't skip the file just because the match isn't total — a
partial rule is better than no rule.

## Naming convention note

The Halo/GDO split is specific to the first target app. A fixture or app repo with a differently
named BLE stack still gets `ble-halo.instructions.md`/`ble-gdo.instructions.md` written with the
`applyTo` glob adjusted to that repo's actual package path — the filenames stay fixed so
`code-reviewer` and other agents can refer to them by a known name, but the glob inside always
matches the real package.
