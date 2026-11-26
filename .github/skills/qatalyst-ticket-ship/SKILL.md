---
name: qatalyst-ticket-ship
description: >
  /qatalyst-ticket-ship. Checks every task is ticked, runs code-reviewer and
  security-reviewer/error-handling-reviewer where flagged, shows the token
  report, settles the commit message with the developer, runs the local
  build and tests, then asks once and commits, pushes, and opens one
  cross-linked Bitbucket PR per repo touched, in merge order. Checks each
  repo's Pipelines run where Pipelines is on, and moves the ticket to In
  Review once every repo's gate clears.
---

# qatalyst-ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then ship — you don't implement anything
yourself. A ticket's diff can span more than one repo (see `architecture.md`'s module/repo map) —
treat every step below as per-repo unless it says otherwise.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't ship a
   partial ticket.
2. **Review, and fix what the review finds, for up to 3 rounds.** Run `qatalyst-code-reviewer`
   against the full diff in every repo touched; run `qatalyst-security-reviewer` too if
   `qatalyst-code-reviewer` flagged a sensitive area, and `qatalyst-error-handling-reviewer` too if it
   flagged a layer where functions can fail. All must pass with no open comments, in every repo. The
   code reviewer runs on a deeper model than `qatalyst-developer` on purpose, so the second opinion
   isn't the model that wrote the code.
   When a reviewer has open comments, that is a round (the first review is round 1):
   1. Note the round: which reviewer, and each comment with its file and what was wrong.
   2. Hand `qatalyst-developer` the exact comments of this round, plus every earlier round's list
      under "what was wrong before", and tell it to fix only those, with the tests the fix needs, and
      to add no other scope. It keeps to `tasks.md` and its own scope rules.
   3. When it reports the fix, run the same reviewers again on the new diff, in every repo touched.
   4. Pass with no open comments: go on to step 3. Otherwise start the next round.
   After round 3 with comments still open, stop. Show the open comments and ask (see
   `qatalyst-ask-developer`): I'll fix it by hand, then check again · Ship anyway, comments open (say
   so in every PR's description) · Cancel. Never push with open comments unless they pick "ship
   anyway".
   When the loop ends, add a "Review rounds" section to `.logs/<ticket ID>/workflow-report.md`, one line
   per round: the reviewer, the comments, and whether the fix cleared them, and how it ended (passed in
   round N, or open after 3). If that file isn't there, say so and give the same lines in chat.
3. **Show the token report**, now that the review is done and the diff is final. Only in VS Code,
   when the ticket was marked (you were told "Token tracking: on", or `.logs/token-tracker/markers.jsonl`
   has a line for this ticket), run
   `python3 .github/token-tracker/scripts/token_tracker.py report <ticket ID> --open` and show the
   summary it prints: the total tokens and the split by agent and model. It opens `token-usage.html`
   in the browser; where it can't, it prints the file's path, so pass that on. Say the push and PR
   steps aren't in it, and that running the command again after shipping adds them. If it fails or
   finds no calls, say so in one line and carry on. Otherwise skip this step without comment and
   create no files.
4. **Settle the commit message.** Run the `qatalyst-commit-message` skill: it writes each repo's
   commit title and message from the diff, shows them, and lets the developer rework them (shorter,
   more detail, or their own wording) until they pick "Use this message". A message approved earlier
   by `qatalyst-ticket-start`'s "ship later" path is reused if that repo's files haven't changed
   since. If a later step changes the diff (a fix after a failed test, say), run the skill again
   before step 6.
5. Build locally with `isLocalBuild=true`, in every repo touched, then **ask the developer which
   tests to run** (see `qatalyst-ask-developer`) and run them the same way, using the commands in
   `project-context.md`'s "Build and test commands". If those are still marked TBD, say which
   command you're about to run before running it. The options:
   - **Unit tests** in every module touched (recommended).
   - **All tests**: unit tests, then the instrumented (`androidTest`) tests. These need an emulator
     or device; check one is connected first (`adb devices`), and if none is, say so and ask again
     rather than skipping them.
   - **Only this ticket's tests**: the test classes the diff added or changed, in their modules (leave
     this option out when `tasks.md` says `**Tests:** none`: there are none).
   - **Skip tests**: build only. Say "tests were not run locally" in every PR's description, and
     never report them as passing.

   When `tasks.md` has a "Fix check" item under Open questions (the developer chose to go ahead
   despite a finding), say it in every PR's description in one line: the finding and that the
   developer chose to proceed, so the reviewer knows.

   When `tasks.md` says `**Tests:** none`, say in every PR's description "No tests written for this
   change (developer's choice at approval)"; running the existing tests is still offered above.

   Where a module's build ignores test failures (see `testing.instructions.md`), read its test
   report instead of trusting the exit code. Plan-only tests (interop, OTA, performance, chaos) have
   no Gradle task; they aren't part of this choice. If tests fail, show which and stop; don't push.
6. **Ask the developer once**, showing: the approved commit title in
   each repo, the planned PRs and their merge order (which repo depends on
   which), the files that will be pushed in each, each PR's title and description, and the workflow
   report's summary (the analysis passes, the blast radius) and its "Repowise:" line from
   `.logs/<ticket ID>/workflow-report.md`, giving its full path (if that file isn't there, say so). Ask with
   options, per `qatalyst-ask-developer`: push and open the PRs, or cancel. Do nothing in steps 7–9
   until they pick "push".
7. On confirmation, commit with the approved message from `.logs/<ticket ID>/commit-message.md` (never a
   different one), push the ticket branch (`bug/<ticket ID>-<slug>` or `feature/<ticket ID>-<slug>`, as
   `qatalyst-ticket-start` named it) in each repo, and open one
   cross-linked Bitbucket PR per repo, in merge order. When continuing a ship that a broken chat
   left partway, check each repo first and skip the push or PR it already has. The spec folder
   (`specs/<bug|feature>/<ticket ID>/`) ships in whichever repo owns it (see `architecture.md`'s
   module map) — never duplicated across repos.
8. Check whether Bitbucket Pipelines is on for each repo (see `pipelines-detection.md`'s three-step
   check, run independently per repo). Where it's on, wait for that repo's PR's Pipelines run to
   pass. Where it's off, say so in that PR's description instead of waiting for a check that won't
   appear.
9. Once every repo's gate clears, move the Jira ticket to In Review.

## If the Bitbucket tools aren't available

Push every branch anyway, then print each repo's PR title and description for the developer to
paste into Bitbucket by hand — don't block the whole ship step on one missing tool.

## Rules

- Never push or open any PR before the single confirmation in step 6 — one confirmation covers every
  repo, not one ask per repo. The commit message is settled before it (step 4), with its own question.
- Never commit with a message the developer hasn't approved.
- Never report a repo's Pipelines check as passing without actually reading that repo's run (Rovo
  MCP's pipeline-runs tool for that PR's source commit, falling back to the REST
  `pullrequests/{id}/statuses` endpoint).
- Never move the ticket to In Review until every repo's gate has cleared — one repo passing doesn't
  clear the others.
- Never wait silently on a local build, a test run or a Pipelines run. If a build or test command
  has printed nothing new for 10 minutes, or a Pipelines run hasn't finished after 30, tell the
  developer which one and ask the stuck question from `qatalyst-ask-developer`. Don't push or move
  the ticket meanwhile.
