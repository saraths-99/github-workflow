---
applyTo: "**/commonsdk/**/halo/**,**/spectrumsdk/**"
---

# Halo BLE conventions

- The Halo stack (`commonsdk` + `spectrumsdk`) is a separate Nordic BLE implementation from the GDO
  stack — see `ble-gdo.instructions.md`. Never share connection state, queues, or secure-channel code
  between the two; see `architecture.md` for why they're kept apart.
- Every new command goes through the existing command queue, not a direct GATT write — see the
  `qatalyst-new-ble-command` project skill.
- Every command has a timeout and an explicit error mapping into `Result<T, ModuleError>` — no
  bare GATT callbacks surfacing into the repository layer.
- No key material, token, or raw BLE payload in a log statement — see `data-layer.instructions.md`'s
  storage rule and the `protect-secrets` hook, which also blocks these in shell commands and PR text.
- New commands get a fake-device test (see `testing.instructions.md`) — a real Halo lock is never
  required to exercise the command's logic.
- The Halo stack spans several `LockModelNumber` values, not one device — including HaloKeypad,
  HaloTouchscreen, HaloSelect, HaloSelectPlus, HaloPuck ("Powerbolt 255"), HaloFingerprint ("Halo
  Touch"), Aura, and AuraReach. Capability is modeled per lock class via composable interfaces
  (`AccessCodeAccessible`, `FingerprintAccessible`, `ScreenSecurable`, `WifiProvisionable`,
  `OpStatusControllable` — see `LockAlaCarteInterfaces.kt`), not a single model flag: e.g.
  `HaloFingerprintLock` carries fingerprint records only (no access-code records), and
  `AuraReachLock` is not `WifiProvisionable` (Bluetooth/Matter only). A new command must branch on
  the relevant `is <Interface>` check rather than assuming every `SpectrumLock` supports it, and its
  fake-device test should cover a model that lacks the interface where that distinction matters.
