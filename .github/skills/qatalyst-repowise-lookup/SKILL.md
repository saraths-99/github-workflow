---
name: qatalyst-repowise-lookup
description: >
  How to use Repowise, with its fallback — the shared check-once-per-task
  pattern repeated across planners, developer, reviewers, and log analysis.
---

# qatalyst-repowise-lookup

Used by every agent that cites "Repowise, or a direct read if unavailable" — `qatalyst-bug-planner`,
`qatalyst-feature-planner`, `qatalyst-developer`, `qatalyst-log-analyser`, `qatalyst-code-reviewer`,
`qatalyst-security-reviewer`, and `qatalyst-error-handling-reviewer`. This skill is the mechanics;
each caller states only *what* it's looking up.

## Steps

0. `qatalyst-ticket-start` checks Repowise once at the start of the ticket, asks the developer to
   set it up if it isn't ready, and tells you the outcome. "Ready": use it, with no check of your
   own. "The developer chose to continue without it": go straight to direct file reads, and don't
   ask again. Told nothing (you were started directly): use step 3's own check.
1. Try Repowise first for the lookup the caller needs — real callers of a class, an existing
   signature, a code map, change risk, or why a pattern is the way it is. The index covers every
   repo in the workspace, so for callers, impact and change-risk lookups search all of them, not
   just the repo you're editing (where the tool takes a `repo` argument, pass `all`): a change in
   `commonsdk` or `spectrumsdk` is called from `repository_halo_android`. Name the repo each hit
   came from.
2. If Repowise is unavailable or unreachable, fall back to a direct file read or search for that
   same lookup — never block or retry on Repowise being down. Say so once in your report
   ("Repowise unavailable; used direct file reads, covering only <the repos you read>"), so a reader
   knows the cross-repo callers weren't searched.
3. Check once per ticket/task/review and remember the result. Don't re-check Repowise (or re-fall-
   back) on every subsequent lookup within the same run — one check covers the whole task.

## What this skill is not

Repowise's dead-code/health findings are advisory only — never block a ticket on those alone; that
rule belongs to the caller (`qatalyst-code-reviewer`), not this skill.
