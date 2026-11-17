---
mode: agent
model: ['Claude Sonnet 5.5 (copilot)', 'GPT-6.1 Sol (copilot)', 'Claude Sonnet 5 (copilot)']
description: Add a Halo or GDO BLE command through that stack's queue and secure channel.
---

Run the `qatalyst-new-ble-command` skill for the command described in the argument: confirm the stack (Halo
or GDO) from `tasks.md`, add it through that stack's existing queue with a timeout and error
mapping into `Result`, confirm no key material is logged, then hand off to `qatalyst-test-writer`
for a
fake-device test.
