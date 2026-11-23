---
mode: agent
model: ['Claude Sonnet 5.5 (copilot)', 'Claude Sonnet 5 (copilot)']
description: Write a test for existing code, outside the ticket flow. Usage: /qatalyst-write-tests
---

Run the `qatalyst-write-tests` skill for the code described in the argument: hand off to
`qatalyst-test-writer`,
which routes it to the matching sub-agent(s) the same way it would for a task inside a ticket's
`tasks.md`.
