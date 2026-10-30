<!--
generated-by: copilot-workflow
Keep this file small. Settings block below is read by setup-workflow on every re-run — don't
change its shape. Everything else here is a pointer, not a copy: detail lives in architecture.md,
project-context.md, or a path instruction file under .github/instructions/.
-->
# Copilot instructions for this repo

```yaml
# generated-by: copilot-workflow
jira_projects:
  - key: <JIRA_PROJECT_KEY>
    bug_issue_types: [<BUG_ISSUE_TYPES>]
  # one entry per Jira project this repo's tickets can come from
base_branch: <BASE_BRANCH>
```

## Context docs

- [project-context.md](../project-context.md) — what this app is, who it's for
- [architecture.md](../architecture.md) — layers, modules, stack decisions, and why
<!-- Add these two lines only if the files exist in this repo: -->
- [workflow.prompt.md](../workflow.prompt.md) — documented team workflows
- [docs/workflows/](../docs/workflows/) — workflow detail docs

## Module map

<!-- One line per module: name, role, which repo it lives in if this is a multi-repo ticket -->

| Module | Role |
|---|---|
|  |  |

## Key rules

<!-- Short bullets only — summarize architecture.md, don't restate it. Example shape: -->

- Layers: <!-- e.g. "MVVM + Repository + Services. No use-case layer." -->
- UI: <!-- e.g. "XML + View Binding. No Compose, no Data Binding." -->
- DI: <!-- e.g. "Koin in AppModule.kt." -->
- Errors: <!-- e.g. "kotlin-result, not thrown exceptions." -->
- Storage: <!-- e.g. "Room + SQLCipher. Tokens/keys only in encrypted storage." -->

See the path-specific files under `.github/instructions/` for the detail behind each rule.

## Path instructions in this repo

<!-- List only the files setup-instructions actually wrote, per its detection-map.md -->

-
