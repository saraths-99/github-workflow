---
mode: agent
description: Add a Room entity/DAO change behind a version-bumped migration.
generated-by: copilot-workflow
---

Run the `room-migration` skill for the change described in the argument: make the entity/DAO
change, bump the database version, write the `Migration`, confirm SQLCipher encryption is intact,
then hand off to `test-writer` for a migration test against the previous schema version.
