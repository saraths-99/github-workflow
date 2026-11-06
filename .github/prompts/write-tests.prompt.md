---
mode: agent
description: Write a test for existing code, outside the ticket flow. Usage: /write-tests
---

Run the `write-tests` skill for the code described in the argument: hand off to `test-writer`,
which routes it to the matching sub-agent(s) the same way it would for a task inside a ticket's
`tasks.md`.
