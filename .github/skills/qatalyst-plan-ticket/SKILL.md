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
   pages and Figma designs (read-only — never push a design change), `project-context.md`, and
   `architecture.md`. For a bug, fold in `log-analysis.md`'s root cause and suggested fix rather
   than re-investigating. If `log-analysis.md` lists two candidate root causes instead of one,
   don't pick for the developer — list both under Open Questions with their trade-offs and ask
   which to implement before the task checklist is written. If `log-analysis.md` is instead the
   no-log stub (no attachment, developer confirmed UI-only, log analysis skipped), there is no root
   cause to fold in — step 2 is where you find one instead of re-investigating logs that don't
   exist.
2. Use `qatalyst-repowise-lookup` to ground every claim in the real code — callers, existing signatures,
   and why a pattern is the way it is before changing anything near it. For a no-log bug ticket,
   this step *is* the root-cause investigation: use the ticket's description, comments, and any
   screenshot to identify the affected screen/component, then use `qatalyst-repowise-lookup` and the
   relevant `.github/instructions/` file (`xml-ui.instructions.md` for most UI issues) to pinpoint
   the exact file and cause before writing Approach — a vague "investigate the UI" approach isn't
   acceptable here any more than it would be for a log-backed bug.
3. Write `tasks.md` to `specs/<bug|feature>/<ticket ID>/tasks.md` (see `qatalyst-spec-folder-resolution` —
   deterministic from the ticket's type and ID, nothing to ask about), using the
   `tasks-template.md` shape: What & why,
   Acceptance criteria (Given/When/Then, one per testable behavior), Approach (only the sections
   that apply, citing the module map in `copilot-instructions.md`), Out of scope, Open questions,
   then the ordered task checklist. Each task names the project skill `qatalyst-developer` should
   use and what `qatalyst-test-writer` should cover. The last task is always the review —
   `qatalyst-code-reviewer` (and `qatalyst-security-reviewer` when the diff touches a sensitive
   area) against this ticket's `tasks.md`.
4. Size the file to the ticket — a one-line fix gets a short file and a single task; a cross-repo
   feature gets the full set of stories, criteria, and approach detail.
5. Show the full draft in chat, including the `specs/<bug|feature>/<ticket ID>/` path it lives in.

## Gate

Nothing starts until the developer approves the draft. Once approved, tell the developer a feature
branch is about to be created and the ticket is about to move to In Progress.

## If the plan changes mid-ticket

If `qatalyst-developer` or `qatalyst-test-writer` hits something that invalidates the plan, update
`tasks.md` and get it re-approved before implementation continues — don't let the code and the spec
drift apart silently.
