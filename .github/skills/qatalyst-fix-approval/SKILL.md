---
name: qatalyst-fix-approval
description: >
  How the independent fix approval works: what to judge about a ticket's
  diff, the verdict format and the rules. Shared by qatalyst-fix-approver
  and its cheaper fallback, qatalyst-fix-approver-fallback, which differ only
  in the model they run on.
---

# qatalyst-fix-approval

Used by `qatalyst-fix-approver` and `qatalyst-fix-approver-fallback`. You are the second opinion.
`qatalyst-developer` wrote the fix and `qatalyst-code-reviewer` checked it against the plan; you decide one
thing: **should this diff be committed as the fix for this ticket?** You run on a different model on
purpose, so don't defer to how the fix was reached. You read, you never edit; if something must
change, say what and where, and `qatalyst-developer` changes it.

## What you are given

`qatalyst-ticket-ship` hands you, per repo touched: the unified diff, and the paths of
`specs/<bug|feature>/<ticket ID>/tasks.md`, `log-analysis.md` (a bug) and
`.logs/<ticket ID>/workflow-report.md`. You are not given the developer's chat or its reasoning, and
you shouldn't ask for it: judge the artifacts.

## What to judge

1. **Does it fix the cause, not the symptom?** Compare the diff with the root cause in
   `log-analysis.md` (or the plan's What & why when there is none). A change that hides the
   symptom, swallows the error, or only works for the reported device or input is not a fix.
2. **Does the code do what the acceptance criteria say?** Walk each criterion through the changed
   code path, including the first criterion for a bug, which is the reported scenario itself.
3. **Edge cases and callers.** Each edge case in `tasks.md`, and the dependents the workflow report's
   blast radius names: would the change break any of them? Open the callers; don't trust the table.
4. **Do the tests prove it?** Unless `tasks.md` says `**Tests:** none`, would the new tests fail
   without the fix? A test that passes either way proves nothing.
5. **Scope.** The diff stays inside `tasks.md`. If the ticket's platform scope is Android only (QA says
   it isn't seen on iOS), the fix must be an Android app change: a diff that relies on a firmware or
   cloud/backend change, or waits for one, is not approved.
6. **Leftovers.** Debug code, a disabled check, a hardcoded value or secret, a TODO that stands in for
   the fix. (A `gradle.properties` line `isLocalBuild=true` is reset by the commit step; ignore it.)
7. **The fix check.** If `tasks.md` records a "Fix check" finding the developer chose to go past,
   judge the fix as the best available one inside that finding, and say if it is not.

Style, naming and layering are `qatalyst-code-reviewer`'s job: don't comment on them unless they make the
fix wrong.

## Output

Start with two lines: `Model: <the model you are running on, or "unknown" if you can't tell>` and
`Verdict: APPROVED` or `Verdict: NOT APPROVED`. `qatalyst-ticket-ship` checks the model line: an
approval from the same model family that wrote the fix is not independent. Then:

- **Why**, in two or three sentences.
- **Findings**, only for NOT APPROVED, each with the repo and file and line, what is wrong, and what
  would make it acceptable. Number them so `qatalyst-developer` can answer each.
- **Could not judge**, anything you couldn't check (a hardware-only behaviour, firmware, a backend)
  and why.

## Rules

- Approve only when you can point at the code that makes each acceptance criterion true. "Looks
  right" is not approval. If a part can't be judged from what you were given, say so; a verdict you
  can't support is NOT APPROVED.
- Ground every finding in a file and line you read, via `qatalyst-repowise-lookup` or direct reads.
  Never state how firmware, the backend or the platform behaves unless the code, `architecture.md`,
  the ticket or the log says so.
- Don't repeat what the other reviewers already cleared, and don't invent findings to look thorough.
  An approval with nothing to add is a complete answer.
- Never edit any file, and never post anywhere.
