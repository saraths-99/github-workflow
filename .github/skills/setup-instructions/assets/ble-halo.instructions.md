---
applyTo: "**/commonsdk/**/halo/**,**/spectrumsdk/**"
generated-by: copilot-workflow
---

# Halo BLE conventions

- The Halo stack (`commonsdk` + `spectrumsdk`) is a separate Nordic BLE implementation from the GDO
  stack — see `ble-gdo.instructions.md`. Never share connection state, queues, or secure-channel code
  between the two; see `architecture.md` for why they're kept apart.
- Every new command goes through the existing command queue, not a direct GATT write — see the
  `new-ble-command` project skill.
- Every command has a timeout and an explicit error mapping into `Result<T, ModuleError>` — no
  bare GATT callbacks surfacing into the repository layer.
- No key material, token, or raw BLE payload in a log statement — see `data-layer.instructions.md`'s
  storage rule and the `protect-secrets` hook, which also blocks these in shell commands and PR text.
- New commands get a fake-device test (see `testing.instructions.md`) — a real Halo lock is never
  required to exercise the command's logic.
