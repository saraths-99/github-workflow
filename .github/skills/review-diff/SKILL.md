---
name: review-diff
description: >
  Checks a ticket's diff against tasks.md, the path instructions, both
  context docs, and change risk — the procedure code-reviewer runs on
  every diff.
---

# review-diff

Used by `qatalyst-code-reviewer` for every ticket diff.

## What to check, every time

- Every acceptance criterion in `tasks.md` is actually met by the diff, not just plausible on a
  skim.
- Every task in `tasks.md` that's ticked actually corresponds to a real, present change.
- The diff follows every path instruction file under `.github/instructions/` that applies to the
  files touched.
- The diff is consistent with `architecture.md` and `project-context.md` — no new layer, no
  unexplained module boundary crossing, no silent deviation from a documented pattern.
- **The specs-only rule** — confirm that `qatalyst-bug-planner`/`qatalyst-feature-planner` and
  `qatalyst-log-analyser` only ever touched files under `specs/`, never production code, in this
  ticket's history. Flag it if any of them did.
- Change risk, using Repowise where available: hotspots touched, dependents of a changed class,
  test coverage gaps around the diff. Repowise's dead-code/health findings are advisory only —
  never block a ticket on those alone.

## Output

Post review comments (what's wrong, where, and why) back to the developer. A ticket does not pass
Verify until every comment is resolved and the updated diff has been re-checked.
