---
applyTo: "**/gdosdk/**"
generated-by: copilot-workflow
---

# GDO BLE conventions

- The GDO stack (`gdosdk`) is a separate Nordic BLE implementation from the Halo stack — see
  `ble-halo.instructions.md`. Never share connection state, queues, or secure-channel code between
  the two.
- Commands go through `gdosdk`'s own queue and message handler — don't bypass either, even for a
  "simple" command.
- The secure channel handshake is not to be weakened or skipped for testing — use the fake-device
  test harness (see `testing.instructions.md`) instead of a real GDO unit.
- No key material, token, or raw BLE payload in a log statement — see the `protect-secrets` hook.
- New commands get a fake-device test — see the `new-ble-command` project skill.
