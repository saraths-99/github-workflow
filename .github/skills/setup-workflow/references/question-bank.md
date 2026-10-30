# Question bank

The fixed set of things `setup-workflow` asks the developer in step 3, and nothing else. Ask only
the rows below that step 1 (or the settings block, on a re-run) left unanswered.

| Ask | Exact prompt | Skip when |
|---|---|---|
| Jira project key(s) | "Which Jira project key(s) can this repo's tickets come from? (e.g. `SMARTLOCK`, or `SMARTLOCK, FIRMWARE` if more than one — a multi-repo workspace often tracks each repo's work under its own project)" | Read from the settings block on a re-run |
| Base branch | "What's the base branch new feature branches should fork from? (default: the repo's current default branch, `<detected>`)" | Read from the settings block on a re-run |
| Bug issue type(s), per project | For each key just given: "Which Jira issue type(s) in `<KEY>` mean 'this is a bug'? (default: `Bug`) This is how `ticket-start` decides whether to run `log-analyser` before Requirements." | Read from the settings block on a re-run |
| Notes or a PRD | "Is there a PRD, design note, or anything else you'd like folded into future requirements docs? Paste a link or text, or say no." | Developer says no — don't ask again this run |

## Rules for asking

- Ask all unanswered rows together, in one message, not one at a time — the per-project bug
  issue-type question still goes out in that same message, once per key the developer just gave, not
  as a second round-trip.
- Never re-ask something already answered this run, even across a later skill hand-off.
- Never propose a default for the Jira project key(s) — there's no code signal for them, so always
  ask. Accept one key or several; don't assume a single-key answer means there's only one, and don't
  assume a multi-repo workspace implies multiple keys either — some teams track every repo under one
  project.
- The base branch *can* default to the repo's actual current default branch (read via `git`), shown
  to the developer as a suggestion they can override, not assumed silently.
- Each project's bug issue type(s) can default to `Bug` (Jira's own standard type), shown as a
  suggestion — but if step 1 can read that project's actual Jira issue-type scheme via Atlassian
  Rovo MCP, offer the real list of types instead of guessing at "Bug" alone (some projects use
  `Defect`, `Production Bug`, etc.). Different projects commonly use different schemes — never reuse
  one project's answer as another's default.
- If the developer's answer conflicts with something detected in step 1 — a key they name matches no
  ticket prefix seen in existing branch names across any open repo, *or* a ticket prefix seen in
  branch names matches no key they named — don't argue either way; take their answer as given and
  note the mismatch as a line in the brief (step 4) so they see it before approving.
