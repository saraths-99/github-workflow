---
mode: agent
agent: log-analyser
description: Run the log-analysis loop on a bug ticket before Requirements. Usage: /log-analyser <ticket ID>
generated-by: copilot-workflow
---

Optional manual entry point — `ticket-start` now runs this automatically for any ticket whose Jira
issue type matches its matched Jira project's `bug_issue_types`, so you only need this directly if
you want to look at the logs before deciding to start the ticket at all.

Run the `log-analyser` agent on the ticket ID given as an argument:

1. Intake the ticket **in full** via Atlassian Rovo MCP — description and every comment, since the
   issue time is often only in a comment — and pin the issue time. Note whether the log attachment
   is a plain text file or a `.zip`.
2. Ask which feature this ticket belongs to, from the existing `specs/*/` folders — never default to
   creating a new one; if none fit, say so and ask the developer to confirm before creating one.
3. Run `logcat_extract.py`, then `logcat_trim.py`, then `logcat_digest.py` — no other shell command.
4. Link, Map and Rank root-cause hypotheses, re-running from Link as needed, up to 3 passes.
5. Write `specs/<feature>/<ticket ID>/log-analysis.md`, including a suggested fix, and post a
   redacted Jira comment.
6. Tell the developer it's ready for `/ticket-start`.

If no ticket ID is given, ask for one before doing anything else.
