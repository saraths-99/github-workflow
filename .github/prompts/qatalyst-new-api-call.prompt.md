---
mode: agent
model: ['Claude Sonnet 5.5 (copilot)', 'GPT-6.1 Sol (copilot)', 'Claude Sonnet 5 (copilot)']
description: Add a Halo REST, GDO REST, or AppSync call (DTO, mapper, repository method).
---

Run the `qatalyst-new-api-call` skill for the call described in the argument: add the DTO/GraphQL operation,
a mapper to the domain model, and a repository method returning `Result` using the existing auth
interceptors, then hand off to `qatalyst-test-writer` for a mocked test.
