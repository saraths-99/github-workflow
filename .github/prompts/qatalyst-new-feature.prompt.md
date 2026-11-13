---
mode: agent
description: Implement a feature task end to end, calling the narrower skills as needed.
---

Run the `qatalyst-new-feature` skill for the task described in the argument (or the current `tasks.md` task
in progress, if no argument is given): read its `tasks.md` entry, call `qatalyst-new-screen`/`qatalyst-new-api-call`/
`qatalyst-new-ble-command`/`qatalyst-room-migration` as needed, wire the result into Koin and the nav graph, and hand
off to `qatalyst-test-writer` for anything not already covered.
