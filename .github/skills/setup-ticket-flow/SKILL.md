---
name: setup-ticket-flow
description: >
  Writes ticket-start, ticket-ship and the three spec templates
  (requirements.md, design.md, tasks.md). ticket-start and ticket-ship are
  filled in with the Jira project(s) (key and bug issue type(s) each), base
  branch, repo list and merge order from the approved brief. Run by
  setup-workflow as step 5.6, last in the generation order.
generated-by: copilot-workflow
---

# setup-ticket-flow

You run as step 5.6 of `setup-workflow` — last, because `ticket-start` and `ticket-ship` reference
everything the earlier steps wrote (the agents, the project skills, the hooks).

## 1. Write the spec templates

Copy `assets/spec-templates/*-template.md` to the app repo's `specs/.templates/` (or wherever
`ticket-start` is configured to read a blank spec from — see that skill's own body). These three
are structural scaffolds only — no Jira key or repo list baked in, since a template is reused by
every ticket.

## 2. Write `ticket-start` and `ticket-ship`

Copy `assets/skills/ticket-start/` and `assets/skills/ticket-ship/` to the app repo's
`.github/skills/`, and the matching files in `assets/prompts/` to `.github/prompts/`. Fill in, from
the approved brief:

- The Jira project(s) — each with its key and `bug_issue_types` — and the base branch (same values
  as `copilot-instructions.md`'s settings block) — `ticket-start` uses this in its own step 0: match
  the ticket to one of the configured project keys, then check that project's `bug_issue_types` to
  detect a bug ticket and run `log-analyser` automatically, with no separate manual step.
- The repo list — every repo this app's workspace spans.
- The merge order — SDK/library repos before the app repo, per `architecture.md`'s module graph
  (an SDK repo's PR merges before the app repo's PR that depends on it).

## 3. Hand back to `setup-workflow`

Report the merge order you filled in, so the developer can correct it in the brief review if a
dependency was mis-detected.

## Safety rules for this skill

- Never invent a repo list or merge order — derive it only from the approved brief and
  `architecture.md`'s module graph; ask (via `setup-workflow`'s step 3) if either is ambiguous.
- Never let `ticket-ship` default to assuming Bitbucket Pipelines exists — see
  `references/pipelines-detection.md` for the exact check it must run per repo.
