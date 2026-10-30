---
name: new-ble-command
description: >
  Adds a Halo or GDO BLE command through that stack's existing queue and
  secure channel, with a timeout, error mapping into Result, and a
  fake-device test. Never logs or hardcodes key material.
generated-by: copilot-workflow
---

# new-ble-command

Used by `developer` (directly, or via `new-feature`) for a task that adds or changes a BLE command.
The Halo and GDO stacks are never mixed — pick the one the task's `design.md` entry names.

## Steps

1. Confirm from `design.md` which stack (Halo or GDO) the command belongs to, and read that stack's
   instruction file — `ble-halo.instructions.md` or `ble-gdo.instructions.md` — before writing
   anything.
2. Add the command through the stack's existing command queue — never a direct GATT write.
3. Add an explicit timeout and map every failure path into `Result<T, ModuleError>` — no bare GATT
   callback surfacing past this layer.
4. Confirm no key material, token, or raw payload is written to a log statement anywhere in the new
   code.
5. Hand off to `test-writer` for a fake-device test covering the happy path, the timeout, and at
   least one error mapping — never require a real Halo lock or GDO unit to exercise the new code.

## Done means

The command works against the fake device test harness, respects the existing queue and secure
channel, and the `protect-secrets` hook would find nothing to flag in the diff.
