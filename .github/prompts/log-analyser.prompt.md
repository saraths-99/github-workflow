---
mode: agent
agent: qatalyst-log-analyser
model: ['Claude Opus 5.5 (copilot)', 'Claude Sonnet 5.5 (copilot)']
description: Run the log-analysis loop on a bug ticket before Requirements. Usage: /log-analyser <ticket ID>
---

Optional manual entry point — `qatalyst-ticket-start` now runs this automatically for any ticket whose Jira
issue type matches its matched Jira project's `bug_issue_types`, so you only need this directly if
you want to look at the logs before deciding to start the ticket at all.

Run the `qatalyst-log-analyser` agent on the ticket ID given as an argument:

1. Intake the ticket **in full** via Atlassian Rovo MCP — description, every comment and the
   attachment list, since the issue time is often only in a comment and the log is usually an
   attachment — and pin the issue time. If the ticket has a log but no time, ask the developer for one (or to use
   the whole log) instead of guessing. Note the log attachment's id, name, and whether it is a
   plain text file or a `.zip`.
2. If the attachment isn't in `.logs/<ticket ID>/raw/` yet, fetch it with
   `downloadJiraIssueAttachment` (through the Atlassian `executeRead` tool) and run the `curl` it
   returns, unchanged. If that can't be done, say which step failed and ask the developer to save it
   there. Then run `logcat_extract.py`, `logcat_trim.py` and `logcat_digest.py` — no other shell
   command. If the digest has no warnings or errors, ask the developer (widen the window, use the
   whole log, report it as inconclusive, or stop) rather than ranking a cause from nothing.
3. Link, Map and Rank root-cause hypotheses — Map uses `qatalyst-repowise-lookup` to locate the real class
   and module each error tag belongs to, grounding the fix in actual code. Re-run from Link as
   needed, up to 5 passes.
4. Write `specs/bug/<ticket ID>/log-analysis.md` — deterministic from the ticket ID, nothing to ask
   about — including a suggested fix (or, if the top two hypotheses are still close after the refine
   cap, both candidates and their fixes), and post a redacted Jira comment.
5. Say it's ready for `/qatalyst-ticket-start`.

Every question offers options to pick, per the `qatalyst-ask-developer` skill. If no ticket ID is
given, ask for one first, offering the developer's own open Jira tickets.
