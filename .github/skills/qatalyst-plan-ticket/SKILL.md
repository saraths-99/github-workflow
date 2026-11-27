---
name: qatalyst-plan-ticket
description: >
  Turns ticket inputs (the Jira ticket, Confluence/Figma links, and for a
  bug, log-analysis.md) into one approved tasks.md — the shared mechanics
  behind both bug-planner and feature-planner.
---

# qatalyst-plan-ticket

Used by `qatalyst-bug-planner` and `qatalyst-feature-planner`. Each of those agents states only
what's specific to a bug or a feature; this skill is the shared mechanics of building and gating
`tasks.md`.

## Steps

1. Gather inputs: use `qatalyst-jira-ticket-intake` for the ticket itself, plus any linked Confluence
   pages (Figma links are noted but not fetched: no Figma server is configured), `project-context.md`, and
   `architecture.md`. For a bug, fold in `log-analysis.md`'s root cause and suggested fix rather
   than re-investigating. If `log-analysis.md` lists two candidate root causes instead of one,
   don't pick for the developer — list both under Open Questions with their trade-offs; the
   approval question (see Gate) asks which to implement, and you write the checklist for the
   answer. If `log-analysis.md` is instead the
   no-log stub (no attachment, developer confirmed UI-only, log analysis skipped), there is no root
   cause to fold in — step 2 is where you find one instead of re-investigating logs that don't
   exist.
   Take the ticket's **platform scope** from `qatalyst-jira-ticket-intake` (Android only · also on iOS
   · not stated); see "Android-only tickets" below.
2. Use `qatalyst-repowise-lookup` to ground every claim in the real code — callers, existing signatures,
   and why a pattern is the way it is before changing anything near it. For a no-log bug ticket,
   this step *is* the root-cause investigation: use the ticket's description, comments, and any
   screenshot to identify the affected screen/component, then use `qatalyst-repowise-lookup` and the
   relevant `.github/instructions/` file (`xml-ui.instructions.md` for most UI issues) to pinpoint
   the exact file and cause before writing Approach — a vague "investigate the UI" approach isn't
   acceptable here any more than it would be for a log-backed bug.
3. **Fix check**, before writing anything (see the section below). Only when it finds nothing wrong,
   or the developer says to go ahead, carry on to step 4.
4. Write `tasks.md` to `specs/<bug|feature>/<ticket ID>/tasks.md` (see `qatalyst-spec-folder-resolution` —
   deterministic from the ticket's type and ID, nothing to ask about), using the
   `tasks-template.md` shape: What & why,
   Acceptance criteria (Given/When/Then, one per testable behavior; for a bug, the first one is the
   reported scenario itself, so the fix gets a test that reproduces it), Edge cases (what else could
   go wrong around the change, each tied to the task whose test covers it — drawn from the callers
   and dependents step 2 found, `log-analysis.md`'s unexplained items, and `testing.instructions.md`'s
   checklist), Approach (only the sections that apply, citing the module map in
   `copilot-instructions.md`), Out of scope, Open questions,
   then the ordered task checklist. Each task names the project skill `qatalyst-developer` should
   use and what `qatalyst-test-writer` should cover — the acceptance criteria and edge cases its
   test exercises (write `**Tests:** write` under the title; see the Gate for `none`). The last task is always the review —
   `qatalyst-code-reviewer` (and `qatalyst-security-reviewer` when the diff touches a sensitive
   area) against this ticket's `tasks.md`.
5. Size the file to the ticket — a one-line fix gets a short file and a single task; a cross-repo
   feature gets the full set of stories, criteria, and approach detail.
6. Show the full draft in chat, including the `specs/<bug|feature>/<ticket ID>/` path it lives in.

## Android-only tickets

When the platform scope is **Android only** (QA says the issue is not seen on iOS), the fix is a
change in the Android app repos and nothing else. iOS runs against the same lock firmware and cloud
and works, so those are not where the difference is. Don't plan a firmware or cloud/backend change
as the fix, don't make "ask the firmware or backend team to change it" a task, and don't choose a
firmware or cloud route even when one is possible. Look for what Android does differently: the BLE
stack and its timing, permissions, lifecycle and background limits, threading, OEM behaviour, and the
app's own handling of a response the other platform copes with. A workaround for an Android
platform quirk is an Android fix and is fine. Say in What & why that the ticket is Android only and
why the plan stays in the app. Firmware, cloud and backend areas still go in the report's related
areas, marked "not a fix target: not observed on iOS". For "also on iOS" or "not stated", plan as
usual and let the fix check weigh firmware and cloud.

## Fix check

Before drafting, decide whether a fix is actually there to plan. Look for exactly three findings, and
only when you can point at evidence; a hunch is not a finding, and most tickets have none.

- **Already fixed.** The code the ticket is about already does what the fix would do, so the
  reported scenario can't happen as the code reads now. Cite the file and lines. If only some
  callers or paths are covered, that is not this finding: plan the rest and say in What & why what
  is already done.
- **Blocked.** The fix would need something the app can't do: an OS or platform restriction, a
  store policy (Google Play and the like), a permission the app can't be granted, a limit in
  firmware, a third-party SDK or a backend outside these repos. On an Android-only ticket a
  firmware or backend limit is not a blocker for the fix check: the app change is still the fix, so
  look for an Android-side one first. Cite where you read it: the code, a
  ticket comment, or a linked page. Never assert a policy or platform rule from memory; if you
  can't cite it, or aren't sure it applies, that is **Ambiguous**, not Blocked.
- **Ambiguous.** After steps 1 and 2 you still can't name the file and the change with evidence:
  `log-analysis.md` is inconclusive (or the no-log stub) and step 2 found no cause in the code
  either, or the ticket allows two readings of what "fixed" means and the code doesn't settle it.
  (Two candidate causes in `log-analysis.md` is not this: that has its own question at the Gate.)

On a finding, don't write `tasks.md`. Ask (see `qatalyst-ask-developer`), stating which finding it
is and the evidence: **Do not produce a fix** · **Go with a fix anyway**. If you're running as a
sub-agent and can't ask, return the finding, its evidence and those options to
`qatalyst-ticket-start`, which asks and runs you again with the answer.

- **Do not produce a fix.** Write `.logs/<ticket ID>/no-fix.md` (git-ignored): the finding, the
  evidence, and what would have to change for a fix to be possible (a clearer repro, a decision, a
  permission, a fix elsewhere). Write no `tasks.md`; the flow ends there with no branch, no
  Jira transition and no developer run. Say the file's full path.
- **Go with a fix anyway.** Write `tasks.md` as usual, with the finding as the first item under
  Open questions: `**Fix check (<finding>):**` its evidence, and "the developer chose to go ahead".
  Then plan the best fix that finding allows, never one that pretends it isn't there:
  already fixed → only what the code still lacks (an uncovered caller, a missing test), saying what
  the code already does; blocked → the best workaround inside the limitation, never one that breaks
  the cited policy or permission, with the risk and the manual check named; ambiguous → the most
  likely fix, with the readings you didn't pick listed as alternatives. On an Android-only ticket
  every one of these stays an app change; never a firmware or backend change. If nothing is left to
  change, say so and stop instead of inventing a task.
  Delete `no-fix.md` if it exists.

## Gate

Nothing starts until the developer approves the draft. Ask for approval with options, per
`qatalyst-ask-developer`: approve, request changes (the one answer that takes text), or stop —
plus which root cause to fix, if there are two, plus, the first time the draft is shown, whether to
write tests: **Write tests** (recommended) or **No tests for this ticket**. Ask it in the same call, not
afterwards. Don't ask it again when the draft is shown a second time; its `Tests:` line stands. If
you're running as a sub-agent and can't ask,
return the draft's path and that question to `qatalyst-ticket-start`, which asks it. On "request
changes", revise the draft and ask again. On "No tests", set `**Tests:** none`, delete every task's
Test line and the edge-case "→ Task N's test" ties, and for a bug replace its reproduce-it test with
the manual check named under Open questions (say so there, even if only "no reproduction beyond the
report"). That edit is the developer's own answer applied, not a change to the plan, so it needs no
second approval; say in one line what you removed.

## If the plan changes mid-ticket

If `qatalyst-developer` or `qatalyst-test-writer` hits something that invalidates the plan, update
`tasks.md` and get it re-approved (approve the updated plan, or stop) before implementation
continues — don't let the code and the spec
drift apart silently.
