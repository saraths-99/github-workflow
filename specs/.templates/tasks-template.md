<!--
Filled in by bug-planner or feature-planner, inside specs/<bug|feature>/<ticket ID>/tasks.md. This is
the ticket's only spec file -- what it's for, the approach, and the ordered steps, in one place.
Size this to the ticket: a one-line fix gets a short Context and a single task, not every section
below filled out.
-->
# Tasks — <TICKET ID>: <title>

## What & why

<!-- 1-3 sentences: the user story or problem, from the ticket (+ log-analysis.md's root cause for
     a bug), and the benefit. -->

## Acceptance criteria

<!-- Given/When/Then, one per testable behavior. code-reviewer and test-writer check every one of
     these against the diff before the ticket can ship.
     For a bug, the FIRST criterion is the reported scenario itself: Given the state the report
     describes, When the user does what they did, Then the correct behavior — not the failure. It gets
     a test that reproduces it (and fails without the fix). If an automated test can't reproduce it
     (hardware only, a real device), say why under Open questions and name the manual check. -->

- **Given** ... **When** ... **Then** ...

## Edge cases

<!-- What else could go wrong around this change, and which task's test covers each. Start from the
     callers and dependents Repowise found, log-analysis.md's "still unexplained" list, and the
     checklist in testing.instructions.md (empty or null input, a limit or boundary value, the same
     call twice, cancelled or interrupted partway, the process restarted mid-way), then add what is
     specific to this ticket. A one-line fix may have one or two; write "none beyond the standard
     checklist" only after checking. code-reviewer checks every line has a test, or a stated reason it
     can't. -->

- <edge case> → Task N's test

## Approach

<!-- Only the sub-sections that apply -- omit the rest, don't fill them with "N/A". Cite the module
     map in copilot-instructions.md and ground every claim in the real code via Repowise (or a
     direct read) -- checkable against the current code in under a minute. -->

- **Modules/classes touched:** <!-- what's added or changed, and why -->
- **BLE changes:** <!-- Halo or GDO -->
- **API changes:** <!-- REST and/or AppSync -->
- **Database changes:** <!-- Room entity/DAO + migration version step -->
- **Risks:** <!-- what could break: an existing caller, an encrypted-storage invariant, a BLE
  secure-channel assumption, a module boundary crossing -->

## Out of scope

<!-- Explicit. Especially important when the ticket text is ambiguous about where it stops. -->

-

## Open questions

<!-- Anything not resolved from the ticket, Confluence, Figma, or the context docs. Record the
     developer's answer here once given, rather than deleting the question. -->

-

## Tasks

<!-- One block per task. Tick the checkbox only once its code AND test both exist and pass locally. -->

- [ ] **Task 1 — <short description>**
      Skill: <qatalyst-new-screen | qatalyst-new-ble-command | qatalyst-new-api-call | qatalyst-room-migration | qatalyst-new-feature>
      Test: <what test-writer covers — which acceptance criteria and edge cases>

- [ ] **Task 2 — <short description>**
      Skill: <skill>
      Test: <what test-writer covers — which acceptance criteria and edge cases>

<!-- ... one block per task ... -->

- [ ] **Review — code-reviewer, and security-reviewer/error-handling-reviewer if flagged**
      Against: every acceptance criterion above, and every ticked task

---
*This file is re-approved if the plan changes mid-ticket — see `qatalyst-bug-planner`'s /
`qatalyst-feature-planner`'s
own rule on that.*
