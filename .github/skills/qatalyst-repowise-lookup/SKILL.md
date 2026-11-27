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

## Workflow report

`qatalyst-developer` writes this once every task in `tasks.md` is ticked. It shows how the bug
analysis went (how many passes it took to reach a confident fix), what the ticket's change can
reach (its blast radius), which areas outside the changed code could affect the fix, and whether
Repowise's index was used for it. Write it to
`.logs/<ticket ID>/workflow-report.md` (git-ignored, like the token report), then tell the developer.

1. **Analysis passes (bug tickets).** Read the "Analysis passes" section of
   `specs/bug/<ticket ID>/log-analysis.md` and copy it: how many of the 5 allowed passes the log
   analysis took, a line per pass, and how it ended. Don't recount or reinterpret it. For a feature
   ticket write "Not a bug ticket: no log analysis". If the section isn't there (an analysis from
   before this was recorded), write "not recorded".
2. **What changed.** In every repo touched, list the files the ticket changed against `base_branch`,
   uncommitted work included (`git diff` and `git status`), and the classes, functions and public
   signatures changed in each production file.
3. **Who depends on it.** For each changed production symbol, find its callers and importers in
   every repo of the workspace, with Repowise's references lookup (for example `get_context` with
   references), and name the repo and file of each. A change in `commonsdk` or `spectrumsdk` can
   reach `repository_halo_android`.
4. **How risky.** Ask Repowise for the change risk of the changed files together (for example
   `get_change_risk`), and `get_risk` for any widely imported file; note hotspots among them. Note
   which changed symbols have a test that references them and which have none.
5. **Related areas that could affect the fix.** The code can be right and the fix still fail because
   of something it depends on that this ticket doesn't change. Look for these, only where the
   change, the ticket or `log-analysis.md` actually points at them:
   - **Lock firmware.** A BLE command or response the fix relies on, a firmware version or
     capability check, or the OTA/firmware-update modules (`android_otau`, `commonsdk`'s firmware
     module, `WifiOtaServiceImpl`); and which `LockModelNumber` values reach the changed code, since
     the models differ in what they support.
   - **The other BLE stack.** A change under the Halo stack (`commonsdk` + `spectrumsdk`) or the GDO
     stack (`android_gdo_sdk`) that the other one might share a class, queue or constant with.
   - **The backend and cloud.** REST interfaces, response shapes, auth or cloud-side behaviour the
     fix reads or writes.
   - **The platform.** Android versions, Bluetooth permissions and background limits, OEM
     differences, Google Home/Matter and Android Auto integrations.
   - **Third-party and sibling modules.** Nordic's mcumgr (there are two implementations here), other
     vendor SDKs, and modules in other repos that consume the changed code.

   When the ticket's platform scope is **Android only**, list the firmware, backend and cloud areas
   anyway, but write "Not a fix target: not observed on iOS" in the Check column and put the
   Android-side areas (the platform, the BLE stack, the app's own handling) first.

   For each area you list, give the evidence (the file and line, the ticket text or the log line
   that points to it), why it could change the outcome, and one concrete thing to check or who to
   ask (the firmware team, the backend team, a specific device model or Android version). Never state
   how firmware, the backend or the platform behaves unless the code, `architecture.md`, the ticket
   or the log says so; where it is only a possibility, say "unknown, needs checking". Don't list an
   area just because it exists. If nothing applies, write "None found" and name what you looked at.
6. **Is the index current.** Repowise flags files with uncommitted edits as stale until
   `repowise update --working-tree` runs. Record each changed file as current, stale or not indexed.
   Never run that command yourself (see `qatalyst-ticket-start`'s Repowise check); tell the developer
   to, then to ask you to refresh the report.
7. **Write the file**, in this shape:

   ```
   # Workflow report — <ticket ID>
   Generated <UTC time>, against <base_branch>, uncommitted changes included.

   ## Summary
   Analysis passes (N of 5, or n/a), files changed (and in how many repos), symbols changed,
   dependents found (and how many are in repos other than the one changed), the highest-risk file
   and why, which changes have no test, and how many related areas could affect the fix.

   ## Bug analysis
   Passes: N of 5. One line per pass: what changed and how the confidence moved. How it ended: one
   clear cause · two close candidates · inconclusive at the cap. (Feature: not a bug ticket. Skipped
   or no-error log: say which.)

   ## Related areas that could affect the fix
   | Area | Why it could matter | Evidence | Check or ask |
   |---|---|---|---|
   Firmware, backend, platform, the other BLE stack, third-party or sibling modules. "None found",
   with what was looked at, if nothing applies. Anything only possible is marked "unknown, needs
   checking".

   ## Repowise
   - Used for this report: yes · partly · no (direct search), and why
   - At ticket start: ready (N repos indexed) · the developer continued without it
   - Changed files in the index: N current, M stale, K not indexed
   - Not recorded here: lookups made earlier (planning, log analysis, tasks)

   ## Review rounds
   Added by `qatalyst-ticket-ship` after the review loop, not by this skill. Leave it out when you
   write the report.

   ## Independent approval
   Added by `qatalyst-ticket-ship` after the review loop, not by this skill. Leave it out when you
   write the report.

   ## Workflow checks
   Self-reported by the developer agent from what it was told and what its commands returned.
   - Token tracking: report written (path) · off · not told (no hand-off received) · failed (reason)
   - Token tracking hand-off: received "on" · received "off" · none received
   - Repowise index: ready at ticket start · developer continued without it
   - Repowise commit hook: installed · not installed · not recorded

   ## Blast radius
   ### Changed
   | Repo | File | Change | Symbols changed | In the index | Risk |
   ### Who depends on it
   | Changed symbol | Dependent (repo: file) | Found by (Repowise or direct search) |
   ### Tests around the change
   What covers each changed symbol, and the gaps.
   ### Not covered or unknown
   Anything the lookups could not reach.
   ```
   For "Workflow checks", copy what you were told at the start of the run and the outcome of the
   token report step; write "not recorded" for anything you weren't told. Never infer a check passed.
8. **Tell the developer**, in chat, in a few lines: for a bug, how many passes the analysis took; the
   counts from the Summary and the highest-risk file; a line starting "Related areas:" naming each
   area that could affect the fix, or "none found"; a line starting "Repowise:" saying whether its
   index was used (every lookup · some, naming the ones that fell back · none, and why); any token tracking line that is not "report written" or "off"; any stale
   files with the command to run; and the report's path.

**Without Repowise** (unavailable, or the developer chose to continue without it): still write the
report, from direct searches of the changed symbol names in every repo folder you can read, mark
every blast radius row "direct search", set "Used for this report" to "no" with the reason, and say
that callers in repos you didn't search may be missing. Never present a direct-search report as a
Repowise one.

## What this skill is not

Repowise's dead-code/health findings are advisory only — never block a ticket on those alone; that
rule belongs to the caller (`qatalyst-code-reviewer`), not this skill.
