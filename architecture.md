<!--
FILL IN BY HAND, once, from the real code — see docs/field-sources.md for what counts as solid
evidence per field. Remove any section that has nothing to say for this repo — do not fill it with
"N/A". Once written, this file is never regenerated — edit it directly as the architecture changes.
-->
# Architecture

## Layers

<!-- e.g. "MVVM + Repository + Services. Business logic lives in services; no use-case layer." -->

## Modules

<!-- The module graph from settings.gradle.kts, one line per module, with its role and what it
     depends on. This section is read directly, not inferred. -->

| Module | Role | Depends on |
|---|---|---|
|  |  |  |

## UI

<!-- View Binding vs. Compose vs. Data Binding; BaseFragment or similar base class; navigation
     approach (single host Activity, Safe Args, etc.) -->

## Dependency injection

<!-- Koin module locations, or manual DI per-module if that's what's found -->

## Networking

<!-- REST client(s), GraphQL/AppSync, auth interceptors -->

## BLE

<!-- Each stack found, kept separate: its package, queue/command pattern, secure-channel approach -->

## Storage

<!-- Room, encryption mechanism if any, migration conventions -->

## Error handling

<!-- kotlin-result vs. exceptions vs. a mix — note any inconsistency found rather than averaging it -->

## Testing conventions

<!-- Test dispatcher setup, fake vs. mock usage, where tests live per module -->

## Known risks / deviations from the above

<!-- Anything that doesn't fit the pattern cleanly — a module using Compose, a repo with manual DI
     where the rest use Koin, etc. Listed as fact, not judged. -->

---
*Each fact is cited at the point it's stated; anything without a citation is `TBD`.*
