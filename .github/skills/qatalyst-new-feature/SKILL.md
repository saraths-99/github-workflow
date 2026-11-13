---
name: qatalyst-new-feature
description: >
  Implements a feature task end to end: Fragment, ViewModel, service,
  repository and datasource, wired into Koin and the nav graph. Calls the
  narrower skills (qatalyst-new-screen, qatalyst-new-api-call, qatalyst-new-ble-command, qatalyst-room-migration)
  rather than duplicating their steps.
---

# qatalyst-new-feature

Used by `qatalyst-developer` for a `tasks.md` task that spans the full stack — not just one layer.
This
skill is an orchestrator: it decides which narrower skills a task needs and calls them in the right
order, rather than writing a Fragment-to-database stack by hand.

## Steps

1. Re-read the task's entry in `tasks.md` (its Approach section and the task block itself) for
   which classes, modules and layers it touches.
2. If it needs a new screen, call `qatalyst-new-screen`.
3. If it needs a new network or AppSync call, call `qatalyst-new-api-call`.
4. If it needs a new BLE command, call `qatalyst-new-ble-command`.
5. If it needs a database change, call `qatalyst-room-migration`.
6. Wire the pieces together using the `qatalyst-koin-wiring` skill, and add the nav destination if step 2
   ran (see `xml-ui.instructions.md`).
7. Hand off to `qatalyst-test-writer` for anything the narrower skills didn't already cover
   end-to-end.

## Rules

- Never skip straight to hand-writing a layer this skill would otherwise delegate — if a narrower
  skill exists for a piece of the task, use it, so that piece gets that skill's own test and
  conventions automatically.
- Follow the module boundaries in `copilot-instructions.md`'s module map — don't create a new
  dependency edge between modules without flagging it to the developer first (whichever planner
  wrote this ticket's `tasks.md` updates it and gets it re-approved).
