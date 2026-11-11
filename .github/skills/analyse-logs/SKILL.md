---
name: analyse-logs
description: >
  Root-causes a bug ticket's logs — extract, trim, digest, link, map, rank,
  refine, report — the log-analysis loop log-analyser runs before Planning.
---

# analyse-logs

Used by `qatalyst-log-analyser` for one bug ticket, before `qatalyst-bug-planner` starts Planning.

## The loop

Follow the steps in order, re-running from "Refine" as needed, up to five passes total:

1. **Intake** — read the Jira ticket **in full** via Atlassian Rovo MCP: the description *and every
   comment*, not just the description. Testers often log the issue time in a comment rather than the
   description, so don't stop at the first timestamp-shaped text you find — scan the whole ticket
   before picking one. Pin the issue time from that text; fall back to a screenshot's visible clock
   or a tester-given video timestamp only if the ticket text itself has no usable timestamp. Also
   note the attachment's file type (`.txt`/`.log` vs `.zip`) — you'll need it in the next step.
2. **Extract** — run `logcat_extract.py` against the raw attachment (whatever type it is), writing
   into `.logs/<ticket ID>/raw/extracted/`. If raw logs aren't in `.logs/<ticket ID>/raw/` yet, ask
   the developer to save them there (or attach them to chat only as a last resort — raw logs should
   not live in chat history). If the attachment is a `.zip`, the script extracts every `.txt`/`.log`
   entry inside it and, when there's more than one, merges them in chronological order — never
   unzip or merge anything yourself. Read only the script's own manifest output (file names, sizes,
   what was skipped and why) — never the extracted text.
3. **Trim** — run `logcat_trim.py` against the extracted log from step 2, with the pinned issue
   time. First check its own `# logcat_trim: N lines -> ...` header line: if it trimmed to 0 (or
   near-0) lines, don't treat that as "no errors in the window" — it usually means either the
   attachment's own dates don't actually cover the ticket's stated issue time (testers sometimes
   attach the wrong capture, or the ticket's timestamp is in a different timezone than the device
   that produced the log), or the window itself is just too narrow. Check the trimmed file's own
   date/time range against the issue time pinned in step 1, widen the window if it's just too
   narrow, and otherwise stop and ask the developer rather than reporting a root cause built on an
   empty digest.
4. **Digest** — run `logcat_digest.py` against the trimmed log.
5. **Link** — group digest entries that fire in the same burst or thread, or share an exception
   cause; match any chain already listed in `.github/log-analyser/log-signatures.md`.
6. **Map** — use Repowise (or a direct read, if Repowise is unavailable) to find the class and
   module behind each tag/message, and any recent change to those files.
7. **Rank** — list root-cause hypotheses, each with its evidence lines and the check that would
   disprove it. Note the confidence gap between the top two: a clear leader is one cause, a close
   call is two candidates neither evidence nor a disproof check currently separates.
8. **Refine** (if no single cause explains every error) — re-run Trim with a wider or shifted
   window, or with a dropped noise tag put back; read the suspect code path; or ask the tester for a
   targeted repro. Then repeat from Link. Stop after 5 passes regardless of outcome. If, after 5
   passes, the evidence still doesn't support a single ranked cause, say so plainly in the report
   instead of forcing a best guess — an honest "inconclusive, here's what's missing" is better input
   to Planning than a root cause the logs don't actually support.
9. **Report** — write `log-analysis.md`: the chain from cause to effects, noise excluded, suspect
   classes, and anything still unexplained. If one cause clearly dominates, report it alone: root
   cause, confidence, and **a suggested fix**. If the top two hypotheses remain close after the
   refine cap, report **both** — each with its own evidence, confidence, and suggested fix — rather
   than picking one arbitrarily; `qatalyst-bug-planner` decides with the developer which to
   implement, it's not this skill's call. Either way, this is what lets `qatalyst-bug-planner` move
   on to Planning without a second investigation. Then post a redacted comment on the Jira ticket
   via Atlassian Rovo MCP. Never post anything containing a token, JWT, or email — `logcat_trim.py`
   already redacts these, but re-check before posting.

## Handing off

Once `log-analysis.md` is written:

- If started by `ticket-start`'s own detection step, just finish — it's waiting and hands off to
  `qatalyst-bug-planner` next.
- If started directly via `/log-analyser`, tell the developer it's ready for `/ticket-start`, which
  picks up this file automatically. Either way, do not start Planning.

## Learn (not this skill's job)

After the fix is confirmed, the *developer* adds the chain, its noise tags, and the fix that
resolved it to `log-signatures.md` — this skill only reads that file, never writes to it.
