# Changelog

All notable changes to this workflow are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), applied to the workflow itself
(agents/skills/hooks/prompts), not to any app repo it's installed into.

Bump `VERSION` and add an entry here for every change that lands in this repo — `install.sh`
reads `VERSION` and the synced commit SHA and writes both into a sync-record file in
the app repo, so this is the only place to check what an app repo is actually running and what
changed since its last sync.

## [0.5.0] - 2026-11-19

### Removed
- `qatalyst-security-reviewer` and `qatalyst-error-handling-reviewer` agents, and their
  `review-security`/`review-error-handling` skill logic. General code quality, security-sensitive
  patterns, and failure-handling correctness are now Rovo's PR Code Reviewer's job, run
  automatically on the opened Bitbucket PR, instead of a reviewer agent in this workflow.

### Changed
- `qatalyst-code-reviewer` is narrowed to only what Rovo's PR reviewer can't see: `tasks.md`
  conformance (acceptance criteria, edge cases, ticked tasks) and the specs-only rule. It lost the
  `agent` and `repowise/*` tools along with the change-risk check and the two reviewers it used to
  flag.
- `qatalyst-ticket-ship` waits on Rovo's PR Code Reviewer per repo, the same way it already waits on
  Bitbucket Pipelines, before moving a ticket to In Review.
- `qatalyst-test-writer`'s routing to `qatalyst-security-test-writer` no longer depends on
  `qatalyst-code-reviewer` flagging a diff — it routes directly from the task touching tokens,
  SQLCipher, Tink, a BLE secure channel, or permissions.

## [0.4.3] - 2026-11-17

### Added
- Edge cases are now planned and checked. `tasks-template.md` has an "Edge cases" section, each line
  tied to the task whose test covers it, drawn from the callers Repowise finds, `log-analysis.md`'s
  unexplained items and a checklist in `testing.instructions.md` (empty or null input, a boundary
  value, the same call twice, cancelled or interrupted partway, a restart mid-way, another caller of
  the same code). The unit-test writer covers them, the test router's "done" requires them, and
  `qatalyst-code-reviewer` checks every one has a test or a stated reason it can't.
- A bug is planned with a way to see it fail: its first acceptance criterion is the reported scenario
  itself, with a regression test that reproduces it (`qatalyst-bug-planner`, `qatalyst-plan-ticket`,
  `testing.instructions.md`). Where a small fix makes it practical, the test is checked to fail
  without the fix; a bug no automated test can reproduce names the manual check under Open questions.
- A green Gradle task is not treated as a passing test run where a module's build ignores test
  failures: `qatalyst-developer`, the ship step and `testing.instructions.md` say to read that module's
  test report.

## [0.4.2] - 2026-11-17

### Added
- A model per agent, in three tiers, set by `model:` in each agent's frontmatter as a list of
  `<name> (copilot)` entries tried in order, mixing Claude and GPT models. Deep: the chat's model,
  Claude Opus 5.5 (then GPT-6.1 Sol, GPT-5.6 Sol, Claude Sonnet 5.5), pinned by the `qatalyst-ticket`
  agent and the `/qatalyst-ticket-start`, `/log-analyser` and `/qatalyst-ticket-ship` prompts and
  inherited by log analysis, planning and the security review. Standard, Claude Sonnet 5.5 (then
  GPT-6.1 Sol, Claude Sonnet 5): the developer, the code and error-handling reviewers, the test
  router, and the BLE-protocol and security test writers. Fast, GPT-6 Luna (then Claude Haiku 5.5,
  GPT-5.6 Luna, Claude Haiku 4.5): log-ticket intake and the other test writers.
- The other slash-command prompts pin Sonnet 5.5, because VS Code refuses to start a sub-agent on a
  model that costs more than the chat's.
- A static check for the `model:` format, and that the user-invocable agent pins one.

### Changed
- `copilot-instructions.md`'s Model section describes the tiers instead of one model for everything.
  An app repo that already has that file keeps its old section; update it by hand.

## [0.4.1] - 2026-11-17

### Changed
- UI rule: new screens are built in Jetpack Compose; existing screens stay XML with View Binding and
  aren't converted unless a ticket says so. `xml-ui.instructions.md` (which now also applies to
  `compose/`), the `qatalyst-new-screen` skill and prompt, the key rule in `copilot-instructions.md`
  and `docs/field-sources.md` no longer say "do not introduce Compose". A Compose screen with no
  existing one to follow, or no Compose in the build, is reported as a plan mismatch rather than
  guessed at.

## [0.4.0] - 2026-11-17

### Changed
- The hooks now actually run. `guards.json` is rewritten in GitHub Copilot's native hook format
  (`hooks` keyed by `preToolUse` / `postToolUse`, `bash` command entries), which VS Code and the
  Copilot CLI load from `.github/hooks/`; before, it was in a custom format nothing ran. Android
  Studio's Copilot plugin doesn't load hook files yet.
- The four guard scripts are thin wrappers around a new `scripts/guards.py`, which reads both VS
  Code's and the CLI's payloads, prints nothing to let a call through (so the IDE's own
  confirmation still applies), and prints a `permissionDecision` to deny or ask.
- `protect-secrets` now also blocks commands naming a raw log (`cat .logs/<ticket>/raw/...`), which
  the old pattern never matched, while still letting the log analyser's `logcat_extract.py` and
  `logcat_trim.py` read them. Its token check now only applies to Jira, Confluence and PR text, so
  Kotlin code containing `token = ...` isn't blocked.
- `guard-context-docs` asks only on edits to `project-context.md` / `architecture.md`, not reads.
- `hook-protocol.md` and the static hook check describe the native format.

## [0.3.3] - 2026-11-16

### Changed
- Every agent's `tools` also lists Android Studio's own tool names (`read_file`, `list_dir`,
  `get_errors`, `grep_search`, `file_search`, `semantic_search`, `insert_edit_into_file`,
  `create_file`, `run_in_terminal`, `get_terminal_output`) for the VS Code groups it already has,
  so sub-agents started there aren't left without workspace tools. Read-only agents get only the
  read and search names. The sub-agent tool's Android Studio name is still unknown.

## [0.3.2] - 2026-11-16

### Added
- README §2c: setting up and signing in to the MCP servers in VS Code, Android Studio (choose the
  Local agent; add servers under Copilot settings › MCP servers if needed) and the Copilot CLI,
  which servers the flow needs, and what to do when one doesn't connect.

### Changed
- `atlassian-rovo` points at `https://mcp.atlassian.com/v2/mcp`, the URL Atlassian documents now;
  the old `/v1/sse` endpoint was deprecated and retired on 30 June 2026. Install doesn't overwrite
  an app repo's `.mcp.json`, so existing app repos need the URL changed by hand.
- `.github/mcp/jetbrains-mcp.example.json` uses the layout Android Studio's own `mcp.json` has
  (`servers`, headers under `requestInit`) and the new Atlassian URL.

## [0.3.1] - 2026-11-16

### Changed
- Android Studio: the agents that ask the developer list its question tool, `ask_questions` (seen
  registered in Android Studio's Copilot 1.21.0 log), so questions are clickable there too.
- Every agent sets `x-github-copilot-invoke-policy` (`["user"]` for `qatalyst-ticket`, `["model"]`
  for the rest), the field the JetBrains plugin uses to hide agents from its picker in place of
  `user-invocable`. A static check keeps the two in step.

## [0.3.0] - 2026-11-16

### Added
- `qatalyst-ask-developer` skill: every place the workflow stops for the developer is a question
  with options to click (VS Code's `vscode/askQuestions` tool, or `ask_user` in the Copilot CLI,
  including its agent inside Android Studio; numbered options in Android Studio's own Copilot chat),
  never an open-ended prompt. Requesting changes to `tasks.md` is the only
  typed answer.

### Changed
- `/qatalyst-ticket-start` (and the `qatalyst-ticket` picker agent) now carry a ticket through as
  one flow: plan approval, branch, In Progress, `qatalyst-developer` through every task, then
  "Ship it now" runs `qatalyst-ticket-ship`. `/qatalyst-ticket-ship` still works on its own.
- Running `/qatalyst-ticket-start` again on a ticket resumes it instead of starting over: an
  existing draft goes to the approval question, ticked tasks or a feature branch continue from the
  first unticked task, and all tasks ticked goes to the ship question. If the last chat broke
  partway through a task or the ship step (`.logs/<ticket ID>/in-progress.json` is still there), it
  says so and asks whether to continue keeping the changes, restart with them stashed, or stop.
- No ticket ID given: the developer's open Jira tickets are offered to pick from.
- Missing log attachment: "I've attached it now — check again" replaces re-running the command.
- Sub-agents that can't ask the developer return the question to `qatalyst-ticket-start`, which
  asks it; the planners no longer run the approval gate themselves.
- README: Android Studio needs Agent Skills turned on (a preview setting) for the ticket flow.
- `qatalyst-ticket` gains `execute` (for the branch, the token mark and pushing) and the
  `qatalyst-ticket-ship` skill.

## [0.2.1] - 2026-11-16

### Added
- README §2b: how to install Repowise and index the app repo (`repowise init --yes --no-prose
  --no-editor-setup`, then `repowise hook install`), and why editor setup must stay off.

### Removed
- `.github/log-analyser/log-signatures.md`, and `qatalyst-log-analyser`'s step that matched known
  cause chains against it. No script read it, and its noise-tag and tag-to-module tables were never
  filled in; Repowise already does the tag-to-module mapping. Install no longer adds it to app
  repos, but leaves an existing copy alone.

### Changed
- Install copies only what the workflow uses in the app repo. `.github/mcp/` (the JetBrains MCP
  snippet), `docs/field-sources.md` and `.github/hooks/hook-protocol.md` stay in this repo and are
  linked from the README and `workflow-design.md`; install removes copies an older install left.
- macOS and Linux only: removed `install.ps1`, `copilot-tracked.ps1` and the four hook scripts'
  `.ps1` versions, and their entries in `guards.json`. Re-running `install.sh` deletes the hook `.ps1` copies from app repos.

## [0.2.0] - 2026-11-16

### Added
- Per-ticket token tracking (`.github/token-tracker/`): `token_tracker.py mark/collect/report`
  writes one row per model call (`ticketId`, `agentName`, `model`, `inputTokens`, `outputTokens`,
  `timestamp`) plus totals by agent and model to `.logs/token-tracker/<ticket ID>/`, as
  `token-usage.html` (self-contained page, opened in the browser by `report --open`) and
  `token-usage.json` (rows plus `totals` and `byAgent`). Reads VS Code
  Copilot Chat's local trace database and the Copilot CLI's trace file; the Android Studio chat
  panel has no trace export, so Android Studio users run the Copilot CLI through
  `copilot-tracked.sh`/`.ps1`.
- `qatalyst-ticket-start` marks the ticket for tracking first; `qatalyst-developer` shows the
  ticket's token usage and opens the HTML report once every task in `tasks.md` is ticked.
- `install.sh`/`install.ps1` sync `.github/token-tracker/` and create `.vscode/settings.json` with
  the one setting tracking needs, only if the app repo has no such file.

### Changed
- `install.sh`/`install.ps1` download from the `develop` branch instead of `main`.
- README: manual-install steps for a `.zip` download (README §2a), and the `qatalyst-ticket`
  agent-picker entry point.

## [0.1.0] - 2026-11-13

First versioned release. Establishes the baseline this changelog tracks forward from.

### Added
- `qatalyst-ticket` agent-picker entry point alongside `/qatalyst-ticket-start`.
- `qatalyst-log-ticket-intake` sub-agent: splits ticket/comment reading, issue-time pinning, and
  log-attachment identification out of `qatalyst-log-analyser`'s own Intake step.
- Explicit no-log-attachment handling for bug tickets: `qatalyst-log-ticket-intake` asks the
  developer whether a log was forgotten or the issue is UI-only; on confirmation,
  `qatalyst-log-analyser` writes a no-log stub and `qatalyst-bug-planner` grounds the root cause
  itself via `qatalyst-repowise-lookup` instead of folding one in.
- `VERSION` and this `CHANGELOG.md`; `install.sh`/`install.ps1` now write a sync-record file into
  the app repo recording the version, commit SHA, and sync timestamp.

### Changed
- Every agent and skill now carries the `qatalyst-` prefix, including the 8 skill-backed slash
  commands that renamed to match (e.g. `/ticket-start` → `/qatalyst-ticket-start`). `/log-analyser`
  stays as-is, since it's backed directly by the agent, not a skill.
- `review-diff`, `review-security`, `review-error-handling`, and `analyse-logs` — each with exactly
  one caller — folded directly into that caller's own agent body (`qatalyst-code-reviewer`,
  `qatalyst-security-reviewer`, `qatalyst-error-handling-reviewer`, `qatalyst-log-analyser`).
- `docs/workflow-design.md`'s folder-tree and naming-conventions tables corrected to match the
  files actually on disk; dropped the unused `~/.copilot/skills/` row.

### Removed
- `.github/skills/review-diff/`, `review-security/`, `review-error-handling/`, `analyse-logs/` —
  superseded by the agent-body fold above.
