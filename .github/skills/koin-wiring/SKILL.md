---
name: koin-wiring
description: >
  Registers a ViewModel/repository/service in Koin's AppModule.kt — the
  shared wiring step behind new-screen and new-feature.
---

# koin-wiring

Used by `new-screen` and `new-feature` once a new ViewModel, repository, or service exists and
needs registering.

## Steps

1. Add the binding to that module's Koin `AppModule.kt` (see `koin-di.instructions.md`) — never a
   hand-built singleton alongside Koin.
2. Scope it `factory` unless the task's `tasks.md` entry states a reason for a different scope.
3. Confirm the binding resolves everything the new class's constructor needs — a missing dependency
   fails at runtime, not at compile time, so check the constructor against what's already bound.

## Done means

The new class is Koin-registered and resolvable without a manual `get()` workaround anywhere in the
feature code that uses it.
