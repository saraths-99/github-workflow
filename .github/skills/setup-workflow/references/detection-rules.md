# Detection rules

What `setup-workflow` looks for in step 1 (Read), and how confident each signal makes it. Anything
not matched by a rule here goes into the brief as `TBD`, never as a guess.

## Settings block

A re-run is detected by finding, in `.github/copilot-instructions.md`, a fenced block shaped like:

```yaml
# generated-by: copilot-workflow
jira_projects:
  - key: <KEY>
    bug_issue_types: [<TYPE>, ...]
  # one entry per Jira project this repo's tickets can come from
base_branch: <branch>
```

If the file exists but has no such block, or no `generated-by: copilot-workflow` marker anywhere in
it, treat it as developer-authored and do **not** read it as a settings block — ask for the Jira
project key(s), base branch and each project's bug issue type(s) as if this were a first run, and
flag the file in the brief as "existing, not ours."

Each project entry's `bug_issue_types` is what `ticket-start` checks a ticket's Jira `issuetype`
against, once it's matched the ticket to one of the configured project keys, to decide whether to
run `log-analyser` before Requirements — see `setup-ticket-flow`'s `ticket-start` blueprint. Never
leave a project's `bug_issue_types` unset: default to `[Bug]` if nothing more specific was detected
or given for that project.

## Context docs

| Doc | Found when | Missing when |
|---|---|---|
| `project-context.md` | Present at repo root, non-empty | Absent, or present but empty |
| `architecture.md` | Present at repo root, non-empty | Absent, or present but empty |

Never infer the content of a missing doc yourself — that's `setup-context-docs`'s job, and only runs
on explicit hand-off (step 2).

## Architecture signals

| Signal | Looks for | Confidence |
|---|---|---|
| Layering | Classes under `*/services/`, `*/repository/` or `*Repository.kt`, `*ViewModel.kt` | High if all three present |
| No use-case layer | Absence of a `*/usecase/` or `*UseCase.kt` package | High |
| UI toolkit | `viewBinding { enable = true }` or `buildFeatures.viewBinding` in a module's `build.gradle.kts`; XML layouts under `res/layout/` | High |
| Compose present (flag, don't block) | `androidx.compose` dependency anywhere | Note in brief as a deviation from the documented stack |
| Navigation | A single `HomeActivity` (or named activity) hosting a `NavHostFragment`; `safeargs` plugin applied | High |
| DI | `koin-android` dependency, an `AppModule.kt`; separately, any module wiring dependencies by hand (manual DI) | High for Koin modules; manual DI noted per-module |
| Errors | `kotlin-result` dependency; `Result<T, E>` return types in repository/service methods | Medium — sampled, not exhaustive |
| BLE stacks | Nordic BLE library usage inside packages matching `*halo*` vs `*gdo*` (or equivalent names found in the module map) | High once both packages are located |
| Network | Retrofit service interfaces; AWS AppSync client setup (`AWSAppSyncClient` or generated GraphQL client code) | High |
| Storage | Room `@Database` annotation; SQLCipher factory (`SupportFactory`/`SQLiteDatabase.loadLibs`) | High |
| Module graph | Gradle `include(...)` calls in `settings.gradle.kts` across all open repos | High — this is read directly, not inferred |

## Existing assistant files (never written to, only read)

| Path | What's checked |
|---|---|
| `AGENTS.md` | Any rule whose subject (file glob, module, or topic) overlaps a rule this wizard is about to generate — list both rules in the brief, let the developer decide which wins |
| `.agents/skills/*` | Skill folder names — flag any name collision with a skill this wizard would write under `.github/skills/` |
| `.claude/skills/*` | Same check as `.agents/skills/*` |

A collision is never resolved automatically. It is listed in the brief (step 4) and the developer
chooses: rename the generated skill, skip generating it, or leave the existing one as-is.

## Repowise

If a Repowise MCP server is reachable (see `setup-mcp`'s own check), prefer it for: module
boundaries, entry points, and "does this class exist" lookups, instead of a full-repo file read.
Its absence never blocks setup — fall back to direct reads and note in the brief that Repowise
wasn't available for this run.
