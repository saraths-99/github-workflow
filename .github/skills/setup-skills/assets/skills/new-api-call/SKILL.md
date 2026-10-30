---
name: new-api-call
description: >
  Adds a Halo REST, GDO REST, or AppSync call: a DTO, a mapper, and a
  repository method returning Result, using the existing auth interceptors,
  with a mocked test. Covers only the API styles this repo actually has.
generated-by: copilot-workflow
---

# new-api-call

Used by `developer` (directly, or via `new-feature`) for a task that adds or changes a network
call. Read `data-layer.instructions.md` first for the shared rules (Result returns, explicit
mapping, no leaking DTOs past the repository boundary) — this skill adds the per-style detail.

## REST (Halo or GDO)

1. Add the DTO matching the endpoint's response shape.
2. Add a mapper from DTO to the domain model — never return the DTO itself from the repository.
3. Add the repository method, returning `Result<T, ModuleError>`, using the existing Retrofit
   service interface and its existing auth interceptor — never a new, separate HTTP client.
4. Hand off to `test-writer` for a mocked-response test of the repository method.

## AppSync

1. Add or extend the GraphQL operation using the existing generated client code — don't hand-write
   a raw GraphQL string if a generated operation already covers the shape needed.
2. Map the response into the domain model, same rule as REST: no leaking the generated type past
   the repository.
3. Return `Result<T, ModuleError>` from the repository method, same as REST.
4. Hand off to `test-writer` for a mocked test of the subscription/query/mutation path.

## Done means

The repository method's return type is `Result`, its test mocks the network layer (never hits a
real endpoint), and nothing upstream of the repository sees the raw DTO or GraphQL type.
