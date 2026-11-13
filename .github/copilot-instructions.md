<!--
Keep this file small. Everything here is a pointer, not a copy: detail lives in architecture.md,
project-context.md, or a path instruction file under .github/instructions/.
-->
# Copilot instructions for this repo

## Model

Run every agent and skill in this workflow (`qatalyst-ticket-start` and everything it hands off to) on
**Claude Sonnet 5, or a model of equivalent reasoning capability** — not a faster/cheaper tier.
The hard scope rules, approval gates, and ticket-type detection throughout this workflow assume
strong instruction-following; a weaker model is more likely to skip an approval gate or
misclassify a ticket. Pin the model per agent if your tooling supports it.

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
- UI: XML + View Binding.
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
