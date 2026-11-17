<!--
Keep this file small. Everything here is a pointer, not a copy: detail lives in architecture.md,
project-context.md, or a path instruction file under .github/instructions/.
-->
# Copilot instructions for this repo

## Model

Each agent's `model:` frontmatter sets its tier; an agent without one runs on the model of whatever
started it.

- **Deep — Claude Opus 5.5, else GPT-6.1 Sol, GPT-5.6 Sol or Claude Sonnet 5.5:** the ticket chat
  itself (`/qatalyst-ticket-start`, `/log-analyser`, `/qatalyst-ticket-ship` and the `qatalyst-ticket`
  agent switch the chat to it), and with it log analysis, planning and the security review. The
  approval gates and ticket-type detection run here and assume strong instruction-following; a weaker
  model is more likely to skip a gate or misclassify a ticket.
- **Standard — Claude Sonnet 5.5, else GPT-6.1 Sol or Claude Sonnet 5:** implementation, code and
  error-handling review, the test router, BLE-protocol and security tests.
- **Fast — GPT-6 Luna, else Claude Haiku 5.5, GPT-5.6 Luna or Claude Haiku 4.5:** log-ticket intake
  and the other test writers.

A sub-agent can't run on a model that costs more than the chat that started it, so don't switch the
chat to a cheaper model partway through a ticket. Where an IDE ignores `model:`, pick the deep-tier
model in the chat's model picker yourself.

```yaml
jira_projects:
  - key: <FILL IN: your Jira project key>
    bug_issue_types: [<FILL IN: e.g. Bug>]
  # one entry per Jira project this repo's tickets can come from
base_branch: <FILL IN: e.g. main>
```

## Context docs

- [project-context.md](../project-context.md) — what this app is, who it's for
- [architecture.md](../architecture.md) — layers, modules, stack decisions, and why
<!-- Add these two lines only if the files exist in this repo: -->
- [workflow.prompt.md](../workflow.prompt.md) — documented team workflows
- [docs/workflows/](../docs/workflows/) — workflow detail docs

## Module map

<!-- FILL IN: one line per module — name, role -->

| Module | Role |
|---|---|
|  |  |

## Key rules

<!-- FILL IN: short bullets only — summarize architecture.md, don't restate it. Example shape: -->

- Layers: <!-- e.g. "MVVM + Repository + Services. No use-case layer." -->
- UI: existing screens XML + View Binding; new screens Jetpack Compose.
- DI: Koin.
- Errors: <!-- e.g. "kotlin-result, not thrown exceptions." -->
- Storage: Room. <!-- e.g. "Room + SQLCipher. Tokens/keys only in encrypted storage." -->

See the path-specific files under `.github/instructions/` for the detail behind each rule.

## Path instructions in this repo

- `.github/instructions/kotlin.instructions.md`
- `.github/instructions/xml-ui.instructions.md`
- `.github/instructions/koin-di.instructions.md`
- `.github/instructions/ble-halo.instructions.md`
- `.github/instructions/ble-gdo.instructions.md`
- `.github/instructions/data-layer.instructions.md`
- `.github/instructions/testing.instructions.md`
- `.github/instructions/gradle.instructions.md`
