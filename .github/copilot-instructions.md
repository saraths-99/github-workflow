# Instructions for working on this repo

This is the **builder** repo, not an app repo. Nothing here runs against product code directly —
it generates files into a separate Android app repo via the `setup-workflow` skill and its six
`setup-*` helpers.

## Rules for this repo

- **Blueprints are the source of truth.** Every file the builder writes into an app repo comes from
  a reviewed blueprint under some `.github/skills/setup-*/assets/`. Never hand-edit a generated
  example or an app repo's output directly to fix a bug — fix the blueprint, so every app repo
  benefits on its next `/setup-workflow` run.
- **Skill names are unique and stable.** A skill folder's name must match its `name:` field. Don't
  rename a shipped skill; app repos may have it installed under the old name.
- **The `generated-by: copilot-workflow` marker is load-bearing.** Any file a `setup-*` skill writes
  into an app repo must carry this marker (in frontmatter or a header comment, per file type), so a
  re-run can tell its own files apart from hand-written ones and only offer to overwrite its own.
- **Never write into an app repo's `.agents/`, `.claude/`, `.android-studio/` or `AGENTS.md`.** Other
  assistants and Copilot itself read those paths; setup only reads and reports on them, never writes.
- **Context docs are read, never generated as fact.** `setup-context-docs` drafts a missing
  `project-context.md` or `architecture.md` from code analysis, but the draft is marked `TBD` wherever
  evidence is missing and is written only after the developer approves it in chat.
- **No tokens or secrets in any blueprint or fixture.** MCP config templates ship with an empty
  token slot; fixture repos must not contain real credentials, even fake-looking ones that resemble
  a real format.
- **Test changes against the fixtures, not just by reading the blueprint.** Once `fixtures/` and
  `tests/` exist (later phase), a change to a `setup-*` skill should be checked against the fixture
  repos before it's considered done.

## Scope boundary

Do not add product-app logic here (Kotlin, Gradle, BLE code, etc.) — that only ever exists inside
the generated blueprints as example snippets, or inside `fixtures/`. This repo's own code is the
wizard logic, detection rules, and the scripts under `setup-agents`'s blueprints (e.g. the log
trim/digest Python scripts), nothing else.
