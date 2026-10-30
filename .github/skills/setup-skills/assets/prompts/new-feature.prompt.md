---
mode: agent
description: Implement a feature task end to end, calling the narrower skills as needed.
generated-by: copilot-workflow
---

Run the `new-feature` skill for the task described in the argument (or the current `tasks.md` task
in progress, if no argument is given): read its `design.md` entry, call `new-screen`/`new-api-call`/
`new-ble-command`/`room-migration` as needed, wire the result into Koin and the nav graph, and hand
off to `test-writer` for anything not already covered.
