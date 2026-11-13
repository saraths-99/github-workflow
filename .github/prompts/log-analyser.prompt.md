---
mode: agent
agent: qatalyst-log-analyser
description: Run the log-analysis loop on a bug ticket before Requirements. Usage: /log-analyser <ticket ID>
---

Optional manual entry point — `ticket-start` now runs this automatically for any ticket whose Jira
issue type matches its matched Jira project's `bug_issue_types`, so you only need this directly if
you want to look at the logs before deciding to start the ticket at all.

Run the `qatalyst-log-analyser` agent on the ticket ID given as an argument:

1. Intake the ticket **in full** via Atlassian Rovo MCP — description and every comment, since the
   issue time is often only in a comment — and pin the issue time. Note whether the log attachment
   is a plain text file or a `.zip`.
2. Run `logcat_extract.py`, then `logcat_trim.py`, then `logcat_digest.py` — no other shell command.
3. Link, Map and Rank root-cause hypotheses — Map uses `repowise-lookup` to locate the real class
   and module each error tag belongs to, grounding the fix in actual code. Re-run from Link as
   needed, up to 5 passes.
4. Write `specs/bug/<ticket ID>/log-analysis.md` — deterministic from the ticket ID, nothing to ask
   about — including a suggested fix (or, if the top two hypotheses are still close after the refine
   cap, both candidates and their fixes), and post a redacted Jira comment.
5. Tell the developer it's ready for `/ticket-start`.

If no ticket ID is given, ask for one before doing anything else.
