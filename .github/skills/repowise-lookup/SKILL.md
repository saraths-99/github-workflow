---
name: repowise-lookup
description: >
  How to use Repowise, with its fallback — the shared check-once-per-task
  pattern repeated across planners, developer, reviewers, and log analysis.
---

# repowise-lookup

Used by every agent that cites "Repowise, or a direct read if unavailable" — `qatalyst-bug-planner`,
`qatalyst-feature-planner`, `qatalyst-developer`, `qatalyst-log-analyser`, `qatalyst-code-reviewer`,
`qatalyst-security-reviewer`, and `qatalyst-error-handling-reviewer`. This skill is the mechanics;
each caller states only *what* it's looking up.

## Steps

1. Try Repowise first for the lookup the caller needs — real callers of a class, an existing
   signature, a code map, change risk, or why a pattern is the way it is.
2. If Repowise is unavailable or unreachable, fall back to a direct file read or search for that
   same lookup — never block or retry on Repowise being down.
3. Check once per ticket/task/review and remember the result. Don't re-check Repowise (or re-fall-
   back) on every subsequent lookup within the same run — one check covers the whole task.

## What this skill is not

Repowise's dead-code/health findings are advisory only — never block a ticket on those alone; that
rule belongs to the caller (`qatalyst-code-reviewer`), not this skill.
