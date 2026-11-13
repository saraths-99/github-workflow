---
name: spec-folder-resolution
description: >
  Computes a ticket's spec path deterministically from its type and ticket
  ID — the shared mechanics behind qatalyst-log-analyser and
  qatalyst-feature-planner. No folder listing, no developer ask.
---

# spec-folder-resolution

Used by `qatalyst-log-analyser`, `qatalyst-bug-planner`, and `qatalyst-feature-planner`. There is no
folder to pick: the path is always

```
specs/<bug|feature>/<ticket ID>/
```

where `<bug|feature>` is whichever type `ticket-start`'s step 0 (or a direct `/log-analyser` run)
already determined from the ticket's real Jira `issuetype` — never a feature name, never a
developer-chosen or ticket-title-derived slug. The ticket ID alone makes the path unique, so there is
nothing to list, confirm, or re-confirm between agents: `qatalyst-bug-planner` writes to the exact
same path `qatalyst-log-analyser` already used, with no "reuse" step needed because there was never
a choice to reuse.

## Caller-specific rule (not this skill's call)

- **`qatalyst-log-analyser`** — before writing anything to `specs/bug/<ticket ID>/`, locate the real
  code this bug touches: use `repowise-lookup` against the digest's suspect tags/classes (the Map
  step of its own log-analysis loop) so the root cause is grounded in an actual file and caller, not
  a folder name. The folder itself needs no decision; the code location does.

## Done means

One spec path, `specs/<bug|feature>/<ticket ID>/`, ready for the caller's own file write — computed,
not asked about.
