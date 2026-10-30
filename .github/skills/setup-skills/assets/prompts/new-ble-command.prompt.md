---
mode: agent
description: Add a Halo or GDO BLE command through that stack's queue and secure channel.
generated-by: copilot-workflow
---

Run the `new-ble-command` skill for the command described in the argument: confirm the stack (Halo
or GDO) from `design.md`, add it through that stack's existing queue with a timeout and error
mapping into `Result`, confirm no key material is logged, then hand off to `test-writer` for a
fake-device test.
