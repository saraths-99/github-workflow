---
name: setup-workflow
description: >
  Entry point for the Agentic AI-SDLC workflow, run once per app repo via
  /setup-workflow. Reads the repo's context docs and code, confirms a brief
  with the developer, then runs the setup-context-docs, setup-instructions,
  setup-agents, setup-skills, setup-hooks, setup-mcp and setup-ticket-flow
  skills in order to generate the repo's Copilot instructions, agents,
  skills, prompts, hooks and MCP config. Safe to re-run.
generated-by: copilot-workflow
---

# setup-workflow

You are running the setup wizard for the Agentic AI-SDLC workflow. This skill only orchestrates —
each step below is actually carried out by a dedicated `setup-*` skill. Follow the steps in order
and do not skip the approval gates; nothing is written to the app repo before the matching gate is
cleared.

## 0. Detect a re-run

Before anything else, check whether `.github/copilot-instructions.md` already exists and carries a
`generated-by: copilot-workflow` marker with a settings block (see `references/detection-rules.md`
§ "Settings block"). If it does, this is a re-run:

- Read the Jira project key(s) — each with its own bug issue type(s) — and the base branch from the
  settings block instead of asking for them.
- Still re-read the code (architecture may have moved on since the last run).
- Still show the brief and still ask before overwriting any file — a re-run is not a silent update.

## 1. Read

Read, in this order, and note what each one tells you (see `references/detection-rules.md` for the
exact signals to look for in each):

1. `project-context.md` and `architecture.md` at the repo root.
2. `workflow.prompt.md` and anything under `docs/workflows/`.
3. The repos and Gradle modules open in the workspace, their `build.gradle.kts` / `libs.versions.toml`.
4. UI (layouts, nav graphs, `BaseFragment` usage), BLE packages (Halo and GDO stacks), network layer
   (Retrofit, AppSync), DI (`AppModule.kt`, Koin vs. manual DI), and any remote/API clients.
5. Any `AGENTS.md`, `.agents/skills/` or `.claude/skills/` already in the repo — note their skill
   names and rules so step 4 can flag clashes. **Never write to these paths**; read-only.

If Repowise is configured, use it to confirm module boundaries and entry points instead of reading
every file by hand; fall back to direct file reads if it's unavailable.

## 2. Draft what's missing

If `project-context.md` or `architecture.md` is missing, hand off to the `setup-context-docs` skill.
It drafts the missing doc from the code (and Repowise, if present), marking anything it can't find as
`TBD` with the source file cited. **Do not write the draft yourself and do not write it to disk** —
`setup-context-docs` shows it to the developer and writes it only on approval. An existing context
doc is never regenerated or touched, even if it looks stale.

## 3. Ask what the code can't show

Ask the developer, in chat, only for what step 1 could not determine (see
`references/question-bank.md` for the exact prompts):

- Jira project key(s) this repo's tickets can come from — one or more (skip if read from the
  settings block in step 0).
- Base branch (skip if read from the settings block in step 0).
- Which Jira issue type(s) mean "this is a bug," for each project key just given (skip if read from
  the settings block in step 0) — this is what lets `ticket-start` tell a bug ticket from a feature
  ticket automatically; see `references/question-bank.md`.
- Any notes or a PRD the developer wants folded into later specs.

Do not ask about anything step 1 already found with reasonable confidence — ask only for gaps.

## 4. Confirm the brief

Show the developer a single summary in chat with every detected fact and its evidence (file and
line, or module/package name) so they can fix a misread before anything is generated. Include in
the brief:

- Everything detected in step 1, with its source.
- Any skill-name clash or rule conflict found in an existing `AGENTS.md` / `.agents/skills/` /
  `.claude/skills/` (step 1.5).
- Anything still `TBD` from a context-doc draft in step 2.

**Nothing is written past this point until the developer approves the brief as shown, or approves
it with corrections.**

## 5. Generate, in order

Once the brief is approved, hand off to each skill below in turn. A skill only starts once the one
before it has finished; each still shows its own diffs per step 6 — this order is about dependency,
not about skipping review.

1. `setup-instructions` — `copilot-instructions.md` (including the settings block from step 0/3) and
   the path-specific instruction files.
2. `setup-agents` — the seven agents, built using the rules just written in step 5.1.
3. `setup-skills` — the project skills the code needs, plus each one's prompt shortcut.
4. `setup-hooks` — `guards.json`, the hook scripts, and `sensitive-paths.txt`.
5. `setup-mcp` — the MCP server config files (Rovo MCP, Figma, Repowise), token slots left empty.
6. `setup-ticket-flow` — `ticket-start`, `ticket-ship` and the spec templates, filled in with the
   Jira project(s) (key and bug issue type(s) each), base branch, repo list and merge order from
   the brief. Each project's bug issue type(s) are what let `ticket-start` detect a bug ticket and
   run `log-analyser` before Requirements automatically, instead of relying on the developer to
   remember to run `/log-analyser` first.

## 6. Verify

For every file written in step 5: validate it (see each skill's own checks), show the developer a
diff, and ask before overwriting anything that isn't a fresh file. A file without the
`generated-by: copilot-workflow` marker is never touched — it belongs to the developer, not this
wizard.

## 7. Hand off

Tell the developer what's left for them to do by hand, and do not attempt any of it yourself:

- Commit the generated files.
- Copy `.github/mcp/jetbrains-mcp.example.json` into their own JetBrains `mcp.json` and add their
  Atlassian token.
- If they want Repowise, install and index it separately (this wizard never installs tools).

## Safety rules for this skill

- Never write a file outside the fixed order in step 5, and never write anything before the brief
  (step 4) is approved.
- Never touch `.agents/`, `.claude/`, `.android-studio/` or `AGENTS.md` in the app repo.
- Never fill in a Jira project key, its bug issue type(s), base branch, token, or any other value
  the developer hasn't given you or that isn't in the settings block — leave it `TBD` and ask.
- If a hand-off skill in step 5 fails validation, stop the chain at that step; do not run later
  skills against a broken earlier one.
