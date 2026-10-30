---
name: setup-skills
description: >
  Writes the project skills the code actually needs (new-feature, new-screen,
  new-ble-command, new-api-call, room-migration, write-tests) and each one's
  prompt shortcut. Run by setup-workflow as step 5.3, after setup-agents.
  new-ble-command and room-migration are only written when BLE or Room is
  detected; the rest are always written.
generated-by: copilot-workflow
---

# setup-skills

You run as step 5.3 of `setup-workflow`, after `setup-agents`. These are the skills `developer` and
`test-writer` actually use while implementing a ticket's tasks — distinct from the `setup-*`
builder skills that only ever run once, during setup itself.

## 1. Decide which skills apply

Use `references/detection-map.md` — it reuses the same signals `setup-instructions` already
detected (see its own `detection-map.md`), so you do not re-scan the code yourself.

| Skill | Written when |
|---|---|
| `new-feature` | Always |
| `new-screen` | Always (XML + View Binding is the v1 baseline) |
| `new-ble-command` | A Halo and/or GDO BLE stack was detected — see note below |
| `new-api-call` | Always; its content covers only the API styles actually detected (Halo REST, GDO REST, AppSync — any subset) |
| `room-migration` | Room was detected |
| `write-tests` | Always |

**`new-ble-command` note:** if only one of Halo/GDO is present, still write the skill, but trim its
body to that one stack — don't leave instructions for a stack that doesn't exist in this repo.

## 2. Write each skill and its prompt

Copy the matching folder from `assets/skills/` to the app repo's `.github/skills/`, and the matching
file from `assets/prompts/` to `.github/prompts/`. Every main project skill gets a prompt shortcut —
there is no project skill here without one.

## 3. Hand back to `setup-workflow`

Report which skills were written and which were skipped (and why), for the brief summary and the
step-6 diff review.

## Safety rules for this skill

- Never write `new-ble-command` or `room-migration` when their signal wasn't detected — an app with
  no BLE stack or no Room database doesn't need instructions for either.
- Never hand-edit a skill's blueprint per repo — if a skill's instructions are wrong for a
  particular repo's conventions, that's a signal the blueprint itself needs a more general
  detection branch, not a one-off patch.
- Keep each skill pointed at the path instruction files and agents from phases 4 and 5 rather than
  restating their rules.
