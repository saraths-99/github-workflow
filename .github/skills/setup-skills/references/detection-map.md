# Detection map

Reuses the signals `setup-workflow` gathered in its Read step (see
`setup-workflow/references/detection-rules.md`) and the same conditions `setup-instructions` already
applied to its own path files (see `setup-instructions/references/detection-map.md`).

| Skill | Signal required | Mirrors |
|---|---|---|
| `new-feature` | None | — |
| `new-screen` | XML layouts + View Binding | `xml-ui.instructions.md`'s condition |
| `new-ble-command` | A Halo and/or GDO BLE package | `ble-halo.instructions.md` / `ble-gdo.instructions.md`'s conditions — write the skill if either is present, but only include the sections for the stack(s) actually found |
| `new-api-call` | None required, but content is gated per sub-section: Halo REST section only if a Halo REST client exists, GDO REST section only if a GDO REST client exists, AppSync section only if AppSync is detected | "Networking" row, `setup-workflow`'s detection-rules.md |
| `room-migration` | Room (`@Database`) detected | `data-layer.instructions.md`'s storage rule |
| `write-tests` | None | — |

## When no API style is detected at all

This shouldn't happen for a v1-supported repo (every fixture has at least one network layer), but
if it does, still write `new-api-call` with a note at the top that no REST/AppSync client was found,
rather than skipping the skill entirely — a developer adding the first API call still needs
somewhere to start from.
