# Changelog

All notable changes to this workflow are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), applied to the workflow itself
(agents/skills/hooks/prompts), not to any app repo it's installed into.

Bump `VERSION` and add an entry here for every change that lands in this repo — `install.sh`/
`install.ps1` read `VERSION` and the synced commit SHA and write both into a sync-record file in
the app repo, so this is the only place to check what an app repo is actually running and what
changed since its last sync.

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
