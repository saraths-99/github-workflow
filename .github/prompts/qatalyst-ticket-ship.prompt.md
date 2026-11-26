---
mode: agent
model: ['Claude Sonnet 5.5 (copilot)']
description: Finish a ticket with a local commit — review, token report, commit message, build and tests, then commit. Never pushes or opens a PR. Usage: /qatalyst-ticket-ship
---

Run the `qatalyst-ticket-ship` skill:

1. Confirm every `tasks.md` task is ticked.
2. Run `qatalyst-code-reviewer` (and `qatalyst-security-reviewer`/`qatalyst-error-handling-reviewer`
   if flagged), fixing what they find for up to 3 rounds.
3. Show the token report where tracking is on.
4. Settle the commit title and message with the developer (use it, shorter, more detail, or change
   it).
5. Run the local build and the tests the developer picks.
6. Ask once before committing: commit, or cancel.
7. On confirmation, commit the ticket's files in each repo with the approved message. Nothing is
   pushed, no PR is opened and the ticket isn't moved.
