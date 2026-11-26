---
name: qatalyst-ticket-ship
description: >
  /qatalyst-ticket-ship. Finishes a ticket with a local commit: checks every
  task is ticked, runs code-reviewer and security-reviewer/error-handling-reviewer
  where flagged, shows the token report, settles the commit message with the
  developer, runs the local build and tests, then asks once and commits the
  ticket's changes in each repo touched. It never pushes, opens a pull request,
  checks Pipelines or moves the ticket; the developer does those.
---

# qatalyst-ticket-ship

Run when every task in `tasks.md` is ticked. You verify, then commit locally — you don't implement
anything yourself, and you stop at the commit: nothing is pushed, no pull request is opened, no
Pipelines run is read and the Jira ticket isn't moved. A ticket's diff can span more than one repo
(see `architecture.md`'s module/repo map) — treat every step below as per-repo unless it says
otherwise.

## Steps

1. Confirm every task in `tasks.md` is ticked. If one isn't, stop and say which — don't commit a
   partial ticket.
2. **Review, and fix what the review finds, for up to 3 rounds.** Run `qatalyst-code-reviewer`
   against the full diff in every repo touched; run `qatalyst-security-reviewer` too if
   `qatalyst-code-reviewer` flagged a sensitive area, and `qatalyst-error-handling-reviewer` too if it
   flagged a layer where functions can fail. All must pass with no open comments, in every repo. The
   code reviewer is a separate agent that starts from the diff, `tasks.md` and the context docs, not
   from the developer's chat. It runs on the same deep tier as `qatalyst-developer`, so its
   independence comes from that fresh context, not from a different model.
   When a reviewer has open comments, that is a round (the first review is round 1):
   1. Note the round: which reviewer, and each comment with its file and what was wrong.
   2. Hand `qatalyst-developer` the exact comments of this round, plus every earlier round's list
      under "what was wrong before", and tell it to fix only those, with the tests the fix needs, and
      to add no other scope. It keeps to `tasks.md` and its own scope rules.
   3. When it reports the fix, run the same reviewers again on the new diff, in every repo touched.
   4. Pass with no open comments: go on to step 3. Otherwise start the next round.
   After round 3 with comments still open, stop. Show the open comments and ask (see
   `qatalyst-ask-developer`): I'll fix it by hand, then check again · Commit anyway, comments open
   (the commit message says so) · Cancel. Never commit with open comments unless they pick "commit
   anyway".
   When the loop ends, add a "Review rounds" section to `.logs/<ticket ID>/workflow-report.md`, one line
   per round: the reviewer, the comments, and whether the fix cleared them, and how it ended (passed in
   round N, or open after 3). If that file isn't there, say so and give the same lines in chat.
3. **Show the token report**, now that the review is done and the diff is final. Only in VS Code,
   when the ticket was marked (you were told "Token tracking: on", or `.logs/token-tracker/markers.jsonl`
   has a line for this ticket), run
   `python3 .github/token-tracker/scripts/token_tracker.py report <ticket ID> --open` and show the
   summary it prints: the total tokens and the split by agent and model. It opens `token-usage.html`
   in the browser; where it can't, it prints the file's path, so pass that on. Say the build, tests
   and commit aren't in it, and that running the command again afterwards adds them. If it fails or
   finds no calls, say so in one line and carry on. Otherwise skip this step without comment and
   create no files.
4. **Settle the commit message.** Run the `qatalyst-commit-message` skill: it writes each repo's
   commit title and message from the diff, shows them, and lets the developer rework them (shorter,
   more detail, or their own wording) until they pick "Use this message". A message approved earlier
   by `qatalyst-ticket-start`'s "commit later" path is reused if that repo's files haven't changed
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
   - **Skip tests**: build only. Never report them as passing. Add the line "Tests were not run
     locally." to each commit message and show the messages again with the same question as step 4.

   Where a module's build ignores test failures (see `testing.instructions.md`), read its test
   report instead of trusting the exit code. Plan-only tests (interop, OTA, performance, chaos) have
   no Gradle task; they aren't part of this choice. If tests fail, show which and stop; don't commit.
6. **Ask the developer once**, showing: the approved commit title in each repo, the files that will
   be committed in each, and the workflow report's summary (the analysis passes, the blast radius)
   and its "Repowise:" line from `.logs/<ticket ID>/workflow-report.md`, giving its full path (if that
   file isn't there, say so). Ask with options, per `qatalyst-ask-developer`: commit, or cancel. Do
   nothing in step 7 until they pick "commit".
7. On confirmation, commit in each repo, on the ticket branch (`bug/<ticket ID>-<slug>` or
   `feature/<ticket ID>-<slug>`, as `qatalyst-ticket-start` named it; if a repo is on another branch,
   stop and say so). For each repo:
   - Stage exactly the files in that repo's `Files:` line in `.logs/<ticket ID>/commit-message.md`,
     plus `specs/<bug|feature>/<ticket ID>/` in whichever repo owns the spec folder (see
     `architecture.md`'s module map; never duplicated across repos). Never `git add -A` or
     `git commit -a`, and never stage `.logs/` or a file that isn't in the diff.
   - Commit with that repo's approved title and body, exactly as approved (write it to a temp file
     and use `git commit -F`). No trailer is added.
   - If the commit fails (a hook, say), show the output and stop. Never retry with `--no-verify`.
   - Check with `git log -1 --stat`.

   When continuing a commit that a broken chat left partway, check each repo first and skip the one
   whose latest commit already has the approved title.
8. Say what was done and what wasn't: the commit's short hash and title in each repo, that **nothing
   was pushed, no pull request was opened and the ticket wasn't moved**, and the branch name in each
   repo for the developer to push and open the pull request themselves.

## Rules

- Never commit before the single confirmation in step 6 — one confirmation covers every repo, not one
  ask per repo. The commit message is settled before it (step 4), with its own question.
- Never commit with a message the developer hasn't approved.
- Never push, force-push, amend, open a pull request, read or wait on a Pipelines run, or transition
  the Jira ticket from this skill.
- Never wait silently on a local build or a test run. If a build or test command has printed nothing
  new for 10 minutes, tell the developer which one and ask the stuck question from
  `qatalyst-ask-developer`. Don't commit meanwhile.
