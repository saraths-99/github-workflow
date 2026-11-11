---
name: review-security
description: >
  Checks tokens/keys, SQLCipher, Tink, BLE secure channels, and permissions
  in a diff flagged as security-sensitive — the procedure security-reviewer
  runs.
---

# review-security

Used by `qatalyst-security-reviewer`, only when `qatalyst-code-reviewer` flags a diff as touching a
sensitive area.

## What to check

Use Repowise (or a direct search, if unavailable or unreachable) to find every caller/usage of the
sensitive primitive or pattern you're reviewing, not just the occurrence in this diff — check once
per review and fall back rather than retrying it on every lookup.

- **Tokens and keys** — never written to `SharedPreferences`, plain files, or a log statement;
  always behind the encrypted-storage path described in `data-layer.instructions.md`.
- **SQLCipher** — a Room/database change doesn't weaken or bypass the `SupportFactory`/encryption
  setup; a migration preserves it.
- **Tink** (or any crypto primitive used for key wrapping) — no custom crypto added where an
  existing, reviewed primitive already covers the case; no key material logged or serialized in the
  clear.
- **BLE secure channels** — the Halo and GDO handshake/secure-channel code (see
  `ble-halo.instructions.md` / `ble-gdo.instructions.md`) isn't weakened, skipped, or bypassed for
  convenience, including in test-only code paths that could leak into production.
- **Permissions** — a new or changed Android permission is actually necessary for the feature, and
  is requested at the point of use, not bundled broadly.

## Output

Post review comments the same way `qatalyst-code-reviewer` does. A ticket does not pass Verify
until every comment raised is resolved and the updated diff has been re-checked. If nothing is
wrong, say so explicitly rather than leaving silence that could be read as "not reviewed."
