---
name: room-migration
description: >
  Adds an entity or DAO change behind a Room version bump, with a migration
  that keeps SQLCipher encryption intact, and a migration test.
generated-by: copilot-workflow
---

# room-migration

Used by `developer` (directly, or via `new-feature`) for a task that changes a Room entity, DAO, or
the database schema.

## Steps

1. Make the entity/DAO change.
2. Bump the database version.
3. Write the `Migration` covering exactly this version step — never skip a version or combine
   multiple schema changes into one migration unless the task explicitly covers both.
4. Confirm the migration preserves the existing SQLCipher `SupportFactory` setup — a migration must
   never run against, or produce, an unencrypted database (see `data-layer.instructions.md`).
5. Hand off to `test-writer` for a migration test that runs the real `Migration` against a database
   created at the previous version, not just a schema diff assertion.

## Done means

The migration test passes against the previous schema version, and SQLCipher encryption is
unaffected — confirmed, not assumed.
