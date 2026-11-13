# Agentic AI-SDLC workflow — implementation reference

Design reference for what actually runs inside this repo: the daily ticket pipeline, the
log-analysis loop, the safety mechanisms wrapping all of it, and — in §11 — exactly where every one
of those files lives. Each skill's own `SKILL.md` is the authoritative source for its own
behavior — this document is a synthesis for a single-page view, not a replacement.

This workflow's files are edited directly, in place — there's no wizard, no templating, no
detection logic. The one remaining moving part is `install.sh`/`install.ps1` (see
[README.md §2](../README.md#2-one-time-setup)): a plain file sync, run from inside the actual app
repo, that pulls the latest agents/skills/instructions/hooks/prompts/mcp config from this repo and
overwrites them there — a one-way copy, not a generator run against detected app-repo state.

## 1. One-time manual fill-ins

Three things can't be read off the code or guessed, so `install.sh`/`install.ps1` never overwrite
them once they exist — they're filled in once by hand instead:

- `copilot-instructions.md`'s settings block (`jira_projects`, `base_branch`), module map, and key
  rules.
- `project-context.md` and `architecture.md`, drafted from the real code per
  [`docs/field-sources.md`](field-sources.md), confirmed by a developer, then never regenerated —
  edited directly as facts change.
- MCP tokens, added to your own local config, never committed.

## 2. Daily ticket workflow (spec-driven development)

The shape of it, start to finish. The developer approves every step along the way — nothing moves
to the next box without an explicit yes — and a failed check always loops back to the box before
it, rather than skipping forward.

```mermaid
flowchart TD
    A([Start a ticket]) --> B{Is it a bug?}
    B -- yes --> C[Look at the logs,<br/>find the likely cause]
    B -- no --> D
    C --> D[Plan: tasks.md —<br/>what, why, approach, steps]
    D --> F[Build it, one task<br/>at a time, with tests]
    F --> G[Review the code]
    G --> H[Push the code]
    H --> I{Can we reach<br/>Bitbucket?}
    I -- yes --> J[Open the PR for you,<br/>wait for CI to pass]
    I -- no --> K[Hand you the PR text<br/>to paste in yourself]
    J --> L([Mark ticket In Review])
    K --> L
```

The Plan box is one agent, one file, one approval: `qatalyst-bug-planner` for a bug ticket (after
the
log-analysis loop), `qatalyst-feature-planner` otherwise. Earlier versions of this workflow split
Plan into
three separate files and three separate approvals (requirements, then design, then tasks) written
by two different agents — that meant asking the developer to approve three times, and a duplicate
ask for the feature folder name along the way (one agent resolved it, the next one re-confirmed
it). `tasks.md` now carries what the old `requirements.md` and `design.md` covered — what the ticket
is for, acceptance criteria, approach/risks — as sections ahead of the task checklist, in the single
file `qatalyst-code-reviewer` and `qatalyst-test-writer` check against.

That "Can we reach Bitbucket" step is a real, current gap worth naming plainly: opening a PR and checking CI both need
Bitbucket access through the Atlassian Rovo MCP server, which depends on a scoped API token and an
admin turning on the Bitbucket tools — nothing this workflow controls. Without it, this workflow
never blocks on it; it just hands the developer the PR text to paste in by hand instead (see
`qatalyst-ticket-ship`'s own `SKILL.md`, "If the Bitbucket tools aren't available").

## 3. Log-analysis loop (bug tickets only)

```mermaid
flowchart TD
    A([Intake: read ticket + every<br/>comment, pin issue time]) --> X[Extract: logcat_extract.py<br/>.txt passthrough / .zip merge]
    X --> B[Trim: logcat_trim.py]
    B --> BW{Trimmed to ~0 lines?}
    BW -- yes --> BWX([Stop: ask developer —<br/>wrong file or window, not actually clean])
    BW -- no --> C[Digest: logcat_digest.py]
    C --> D[Link: group + match log-signatures.md]
    D --> E[Map: Repowise class/module lookup]
    E --> F[Rank: root-cause hypotheses]
    F --> G{One cause explains<br/>every error?}
    G -- yes --> H([Report: log-analysis.md<br/>+ suggested fix + Jira comment])
    G -- no, pass < 5 --> I[Refine: widen window /<br/>restore noise tag / read code]
    I --> B
    G -- no, pass = 5 --> H
```

Three scripts in this loop are plain Python, no AI, no network: `logcat_extract.py` normalizes the
raw attachment (a plain `.txt`/`.log` passes through unchanged; a `.zip` is extracted and, if it
holds more than one text log, merged in chronological order) into the single file `logcat_trim.py`
expects, and `logcat_digest.py` groups that trimmed log's warnings and errors by signature.
`log-signatures.md`'s "Tag → module map" is filled in once by hand from a scan of this repo's
`Log.d/Log.w/Log.e` call sites, then kept up to date as new tags are added.

## 4. Agents

Every workspace agent uses the VS Code Copilot custom-agent schema: `.agent.md` under
`.github/agents/`, `target: github-copilot`, supported tool aliases (`execute`, not
`runCommands`), and configured MCP namespaces in `tools` (for example `repowise/*`). These agents
are workflow workers, so `user-invocable: false` hides them from the picker while keeping
model-driven delegation enabled. Agents that delegate include the `agent` tool; agents that use a
repo skill list it in `skills`. The portable server definitions live in the workspace-root
`.mcp.json`.

**Naming migration (complete).** Every agent file and every skill folder in this workflow carries
the `qatalyst-` prefix — the last holdouts (the nine specialized test-writer sub-agents, plus the
13 skills and `log-ticket-intake` that were still unprefixed) were renamed in one pass, along with
every cross-reference and the 8 skill-backed slash commands that renamed to match (e.g.
`/ticket-start` → `/qatalyst-ticket-start`). `/log-analyser` is the one slash command left
unprefixed, since it's backed directly by the already-prefixed `qatalyst-log-analyser` agent, not
by a skill of its own.

| Agent | Job | Copilot tools | Hard scope rule |
|---|---|---|---|
| `qatalyst-log-ticket-intake` | Reads the bug ticket's full text and pins the issue time and log attachment type; `qatalyst-log-analyser`'s own Intake step | read, search, atlassian-rovo/* | Read-only — writes nothing, never touches a log script |
| `qatalyst-log-analyser` | Root-causes a bug ticket's logs with a suggested fix; the loop is its own procedure | read, edit, search, execute, agent, atlassian-rovo/*, repowise/* | Writes only `log-analysis.md`; runs only the three log scripts, in order |
| `qatalyst-bug-planner` | Writes `tasks.md` for a bug ticket, from `log-analysis.md`; mechanics live in the `qatalyst-plan-ticket` skill | read, edit, search, atlassian-rovo/*, figma/*, repowise/* | Writes only `tasks.md`, to the same deterministic `specs/bug/<ticket ID>/` path `qatalyst-log-analyser` already used |
| `qatalyst-feature-planner` | Writes `tasks.md` for a feature ticket; mechanics live in the `qatalyst-plan-ticket` skill | read, edit, search, atlassian-rovo/*, figma/*, repowise/* | Writes only `tasks.md`, to the deterministic `specs/feature/<ticket ID>/` path — nothing to resolve or ask about |
| `qatalyst-developer` | Implements `tasks.md` | read, edit, search, execute, agent, repowise/* | One task at a time, in order, only via the named skill |
| `qatalyst-test-writer` | Routes a task to the matching test-writer sub-agent(s) | read, search, agent, repowise/* | Pure router — no `edit`/`execute` itself; writes nothing |
| `qatalyst-unit-test-writer` | ViewModel/service/repository/mapper/Room tests | read, edit, search, execute, repowise/* | Edits only test files for the in-progress task |
| `qatalyst-ble-protocol-test-writer` | Fake-device BLE command tests | read, edit, search, execute, repowise/* | Edits only test files; never a real lock/GDO unit |
| `qatalyst-androidtest-writer` | Instrumented UI tests | read, edit, search, execute, repowise/* | Edits only `**/androidTest/**` |
| `qatalyst-compatibility-test-writer` | Lock-model capability-matrix tests | read, edit, search, execute, repowise/* | Edits only test files for the in-progress task |
| `qatalyst-security-test-writer` | Tests for security-sensitive logic | read, edit, search, execute, repowise/* | Edits only test files; only runs when flagged by `qatalyst-code-reviewer` |
| `qatalyst-interop-test-writer` | Hardware-in-the-loop interop test plan | read, edit, search, repowise/* | Plan only — writes `test-plans/interop.md`, never code |
| `qatalyst-ota-test-writer` | Firmware OTA test plan | read, edit, search, repowise/* | Plan only — writes `test-plans/ota.md`, never code |
| `qatalyst-performance-test-writer` | Performance/battery test plan | read, edit, search, repowise/* | Plan only — writes `test-plans/performance.md`, never code |
| `qatalyst-chaos-test-writer` | Resilience/fault-injection test plan | read, edit, search, repowise/* | Plan only — writes `test-plans/chaos.md`, never code |
| `qatalyst-code-reviewer` | Reviews diff vs. spec; checklist is its own procedure | read, search, agent, repowise/* | Read-only; checks the specs-only rule on every diff |
| `qatalyst-security-reviewer` | Reviews sensitive-area diffs; checklist is its own procedure | read, search, repowise/* | Read-only; only runs when flagged by `qatalyst-code-reviewer` |
| `qatalyst-error-handling-reviewer` | Reviews failure-handling in services/repos/BLE/API diffs; checklist is its own procedure | read, search, repowise/* | Read-only; only runs when flagged by `qatalyst-code-reviewer` |

Tool lists are the *mechanical* half of scope enforcement (Copilot can strip `edit` outright); the
*written* half — "only these files," "only these commands" — lives in each agent's own blueprint.
`qatalyst-code-reviewer` is the backstop that actually checks the written half was followed.

- **Why reviewers get no edit tool.** Removing `edit` from the tool list is the one scope rule
  Copilot *can* enforce mechanically — so `qatalyst-code-reviewer`, `qatalyst-security-reviewer`,
  and `qatalyst-error-handling-reviewer` all have it removed outright, instead of relying on a
  written instruction alone.
- **Why `qatalyst-test-writer` itself has no `edit` tool.** It's a pure router now — the nine
  specialized writers it hands off to do the actual writing, so `qatalyst-test-writer` needs
  nothing more than `read` and `search` to decide where a task's tests belong.
- **Why four of the nine test-writer sub-agents have no `execute` tool.** `qatalyst-interop-test-writer`,
  `qatalyst-ota-test-writer`, `qatalyst-performance-test-writer`, and `qatalyst-chaos-test-writer` can't execute anything — no
  fake stands in honestly for a real lock, a firmware rig, or a battery-drain bench — so they write a
  markdown test plan under `edit` and nothing more; there's nothing for `execute` to run.
- **Why `qatalyst-log-analyser`'s command scope is written, not mechanical.** Copilot has no
  per-command allowlist in a tool list — "can run commands" is all-or-nothing. So
  `qatalyst-log-analyser`'s blueprint states explicitly that it may only invoke the three named
  scripts; `qatalyst-code-reviewer` isn't the backstop here (its phase is before any code diff
  exists) — the backstop is the developer reviewing `log-analysis.md` and the redacted Jira comment
  it posts.
- **Every `repowise` grant needs its own usage + fallback line.** Granting `repowise/*` in an agent's
  `tools` list isn't self-explanatory — Copilot's tool list has no way to express "try this, then
  fall back," so that behavior is written into the agent's own body: what it uses Repowise for, and
  what to do when it's unavailable (always: fall back to a direct file read/search for that lookup,
  never block or retry). Within one run, check Repowise once and remember the result — don't keep
  retrying it on every subsequent lookup in the same task.

## 5. Skills

| Layer | Skills |
|---|---|
| **Orchestration** | `qatalyst-ticket-start`, `qatalyst-ticket-ship`, `qatalyst-write-tests` (routes to `qatalyst-test-writer` for a standalone test-only task, same as a ticket task) |
| **Implementation** | `qatalyst-new-feature`, `qatalyst-new-screen`, `qatalyst-new-ble-command`, `qatalyst-new-api-call`, `qatalyst-room-migration` |
| **Agent-support** (not a slash command — delegated to by the agents it backs) | `qatalyst-plan-ticket` (`qatalyst-bug-planner`, `qatalyst-feature-planner`) — the only agent-support skill left; `review-diff`, `review-security`, `review-error-handling`, and `analyse-logs` were folded directly into their one respective caller's own agent body (`qatalyst-code-reviewer`, `qatalyst-security-reviewer`, `qatalyst-error-handling-reviewer`, `qatalyst-log-analyser`) since each had exactly one caller and no sharing to preserve |
| **Cross-cutting** (shared mechanics, referenced by multiple agents/skills above rather than restated) | `qatalyst-jira-ticket-intake` (reading a Jira ticket in full, with an issue-time-pinning extension), `qatalyst-spec-folder-resolution` (computing the deterministic `specs/<bug\|feature>/<ticket ID>/` path — no listing, no asking), `qatalyst-repowise-lookup` (the Repowise-then-fallback, check-once pattern), `qatalyst-koin-wiring` (registering a binding in `AppModule.kt`) |

`qatalyst-ticket` is a `user-invocable: true` agent-picker entry point that wraps `qatalyst-ticket-start` with
no procedure of its own — an alternative surface to typing `/qatalyst-ticket-start <ticket ID>`, not a
replacement for it; the two must be kept in sync if `qatalyst-ticket-start`'s flow changes.

## 6. Hooks

The checked-in `guards.json` array and its `{event, tool, paths, command, text}` stdin contract
are the workflow's existing custom guard runner, not VS Code Copilot's native hook format. Changing
agent frontmatter does not activate these guards in a Copilot session. Before relying on them in
VS Code, migrate them to the native `.github/hooks/*.json` command-hook schema and validate the
Copilot event payloads and permission decisions.

| Hook | Event | Denies / does |
|---|---|---|
| `format-kotlin` | `postToolUse` | Runs the formatter on an edited `.kt`/`.kts` file (never denies — event fires after the fact) |
| `block-force-push` | `preToolUse` | Denies a shell command containing `git push` + `--force`/`--force-with-lease`/`-f` |
| `protect-secrets` | `preToolUse` | Denies reads/edits/commands naming a `sensitive-paths.txt` entry; denies text containing a JWT or token-shaped string |
| `guard-context-docs` | `preToolUse` | Asks before `project-context.md`/`architecture.md` is touched; `ask` degrades to `deny` if the agent mode can't ask |

Each script reads one JSON object on stdin (`event`, `tool`, `paths`, `command`, `text`) and writes
one JSON decision (`allow` / `deny` / `ask`) to stdout. A non-zero exit or a 30-second timeout both
fall back — a crash denies the action, a timeout silently allows it (open item 4 in §9). Full
protocol: [`.github/hooks/hook-protocol.md`](../.github/hooks/hook-protocol.md).

## 7. MCP servers

| Server | Used for | Auth |
|---|---|---|
| Atlassian Rovo MCP | Jira, Confluence, Bitbucket Cloud | OAuth (Jira/Confluence); Basic auth API token (Bitbucket) |
| Figma MCP | Linked designs, read-only | Developer's Figma sign-in |
| Repowise | Code map, risk, dead-code (advisory only) | None — local, optional |

## 8. Safety & control principles

- **Developer approves every gate** — each spec file, every task, and the commit/push/PR step all
  wait for an explicit yes.
- **Spec before code** — no feature branch exists until `tasks.md` is approved; `qatalyst-developer`
  can't start a task the spec doesn't list.
- **Context docs are read, not guessed** — `project-context.md`/`architecture.md` are drafted once
  from the real code, cited line-by-line, never regenerated once written.
- **Redact before sharing** — raw logs stay in a git-ignored `.logs/` folder; everything else sees
  only trimmed/digested/redacted output.
- **Mechanical enforcement where possible, written rules elsewhere** — reviewers lose the `edit`
  tool outright; path-scoping ("specs only," "scripts only") is a written rule, checked by
  `qatalyst-code-reviewer`.
- **No secrets in the repo** — both MCP files ship with an empty token slot; `protect-secrets`
  blocks the paths that would leak one.
- **Run on a strong model** — every agent/skill in this workflow expects Claude Sonnet 5 or an
  equivalent-capability model (see `copilot-instructions.md`'s Model section); a weaker model is
  more likely to skip an approval gate or misclassify a ticket than to be caught doing so.

## 9. Known gaps / open risk items

Found by audit, not yet closed — listed here so they stay visible rather than living only in chat:

1. **Test/spec gaming under pressure** — nothing stops `qatalyst-test-writer` from weakening an
   assertion,
   or the "plan changed" re-approval path (`qatalyst-bug-planner`/`qatalyst-feature-planner`) from
   being used to dodge
   a hard bug rather than fix it.
2. **UI error/loading/empty states** — `qatalyst-new-screen` and `xml-ui.instructions.md` stop at wiring;
   nothing requires a screen to handle or test a failure/loading/empty state.
3. **No retry cap for `qatalyst-developer`/`qatalyst-test-writer`** — unlike
   `qatalyst-log-analyser`'s 5-pass cap, nothing
   says "stop and report" after N failed attempts at a task.
4. **Silent hook degradation** — a timed-out guard "falls back to normal permissions" with no
   requirement that the agent notice or disclose it.
5. **"Resolved" is undefined** for review comments — unclear if a developer override counts.
6. **Ticket reclassified after `qatalyst-ticket-start` runs** — issue type is read once; a later
   feature→bug (or reverse) reclassification isn't re-checked.
7. **Technically-passing-but-wrong-approach implementations** — `qatalyst-code-reviewer` checks
   criteria are
   met, not that the approach matches `tasks.md`'s Approach section's intent.
8. **Flaky test passes** — the gate is "passed locally, once"; no rule addresses intermittent tests.
9. **Branch/feature-folder collisions** — no rule for two tickets proposing the same slug.
10. **Plan-only test categories have no execution gate** — `qatalyst-interop-test-writer`, `qatalyst-ota-test-writer`,
    `qatalyst-performance-test-writer`, and `qatalyst-chaos-test-writer` only guarantee a plan file exists and is
    current; nothing in this workflow checks that a human actually ran it against real hardware
    before the ticket ships, or records the result anywhere `qatalyst-ticket-ship` can see.

## 10. Folder structure

Where every file lives in this repo, and which of those paths are a real GitHub Copilot standard
versus a convention this workflow invented for itself.

### 10.1 Repo layout

```
<app-repo>/
├── .mcp.json                         portable workspace MCP servers for Copilot
├── project-context.md                 filled in by hand once; never regenerated
├── architecture.md                    same
├── workflow.prompt.md                 pre-existing team doc, if any — linked, not written here
├── docs/workflows/                    pre-existing team docs, if any
├── docs/workflow-design.md            this document
├── docs/field-sources.md              evidence guide for project-context.md / architecture.md
├── .gitignore                         .logs/ ignored
├── specs/
│   └── .templates/
│       └── tasks-template.md          scaffold only — see §10.3 for the -template.md convention
├── .logs/                             created lazily, git-ignored — see §10.2
└── .github/
    ├── copilot-instructions.md        settings block + module map + key rules + links
    ├── instructions/
    │   ├── kotlin.instructions.md
    │   ├── xml-ui.instructions.md
    │   ├── koin-di.instructions.md
    │   ├── ble-halo.instructions.md
    │   ├── ble-gdo.instructions.md
    │   ├── data-layer.instructions.md
    │   ├── testing.instructions.md
    │   └── gradle.instructions.md
    ├── agents/
    │   ├── qatalyst-ticket.agent.md            user-invocable entry point, wraps qatalyst-ticket-start
    │   ├── qatalyst-log-ticket-intake.agent.md         qatalyst-log-analyser's own Intake step
    │   ├── qatalyst-log-analyser.agent.md
    │   ├── qatalyst-bug-planner.agent.md
    │   ├── qatalyst-feature-planner.agent.md
    │   ├── qatalyst-developer.agent.md
    │   ├── qatalyst-test-writer.agent.md     router only — see below
    │   ├── qatalyst-unit-test-writer.agent.md
    │   ├── qatalyst-ble-protocol-test-writer.agent.md
    │   ├── qatalyst-androidtest-writer.agent.md
    │   ├── qatalyst-compatibility-test-writer.agent.md
    │   ├── qatalyst-security-test-writer.agent.md
    │   ├── qatalyst-interop-test-writer.agent.md     plan only
    │   ├── qatalyst-ota-test-writer.agent.md         plan only
    │   ├── qatalyst-performance-test-writer.agent.md plan only
    │   ├── qatalyst-chaos-test-writer.agent.md       plan only
    │   ├── qatalyst-code-reviewer.agent.md
    │   ├── qatalyst-security-reviewer.agent.md
    │   └── qatalyst-error-handling-reviewer.agent.md
    ├── log-analyser/
    │   ├── scripts/logcat_extract.py
    │   ├── scripts/logcat_trim.py
    │   ├── scripts/logcat_digest.py
    │   └── log-signatures.md
    ├── skills/
    │   ├── qatalyst-new-feature/SKILL.md
    │   ├── qatalyst-new-screen/SKILL.md
    │   ├── qatalyst-new-ble-command/SKILL.md
    │   ├── qatalyst-new-api-call/SKILL.md
    │   ├── qatalyst-room-migration/SKILL.md
    │   ├── qatalyst-koin-wiring/SKILL.md              cross-cutting
    │   ├── qatalyst-plan-ticket/SKILL.md              agent-support, not a slash command
    │   ├── qatalyst-jira-ticket-intake/SKILL.md       cross-cutting
    │   ├── qatalyst-spec-folder-resolution/SKILL.md   cross-cutting
    │   ├── qatalyst-repowise-lookup/SKILL.md          cross-cutting
    │   ├── qatalyst-write-tests/SKILL.md
    │   ├── qatalyst-ticket-start/SKILL.md
    │   └── qatalyst-ticket-ship/
    │       ├── SKILL.md
    │       └── pipelines-detection.md
    ├── prompts/
    │   ├── log-analyser.prompt.md
    │   ├── qatalyst-new-feature.prompt.md
    │   ├── qatalyst-new-screen.prompt.md
    │   ├── qatalyst-new-ble-command.prompt.md
    │   ├── qatalyst-new-api-call.prompt.md
    │   ├── qatalyst-room-migration.prompt.md
    │   ├── qatalyst-write-tests.prompt.md
    │   ├── qatalyst-ticket-start.prompt.md
    │   └── qatalyst-ticket-ship.prompt.md
    ├── hooks/
    │   ├── guards.json
    │   ├── hook-protocol.md
    │   ├── sensitive-paths.txt
    │   └── scripts/  (format-kotlin, block-force-push, protect-secrets, guard-context-docs — each .sh + .ps1)
    ├── mcp/jetbrains-mcp.example.json
```

### 10.2 Per-ticket runtime additions

Not present until a ticket is actually worked; one set per ticket, at a path computed
deterministically from the ticket's type and ID — never a feature-name folder, never asked about.

```
specs/<bug|feature>/<ticket-id>/
├── log-analysis.md      bug tickets only — written by qatalyst-log-analyser
├── tasks.md              written by qatalyst-bug-planner (bug) or qatalyst-feature-planner (feature)
└── test-plans/           only if a plan-only test-writer sub-agent ran for this ticket
    ├── interop.md         written by qatalyst-interop-test-writer
    ├── ota.md             written by qatalyst-ota-test-writer
    ├── performance.md     written by qatalyst-performance-test-writer
    └── chaos.md           written by qatalyst-chaos-test-writer

.logs/<ticket-id>/
├── raw/                 as captured (.txt/.log, or a .zip) — protect-secrets hook blocks Copilot reads
│   └── extracted/        logcat_extract.py's output — same hook applies, still the full raw log
├── trimmed.log           redacted + windowed — what qatalyst-log-analyser actually reads
└── digest.md             error groups with counts and first/last times
```

### 10.3 Naming conventions: specification compliance

Every path under `.github/` conforms to a documented GitHub Copilot customization path, verified
against the [customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet).
Every path outside `.github/` — `specs/`, the `-template.md` suffix — is a project-specific
convention introduced by this workflow; GitHub Copilot has no knowledge of it and assigns it no
behavior.

| Path / suffix | Classification | Notes |
|---|---|---|
| `.github/copilot-instructions.md` | GitHub Copilot specification | Repository-wide instructions |
| `.github/instructions/*.instructions.md` | GitHub Copilot specification | Path-specific instructions; requires an `applyTo` front-matter field |
| `.github/prompts/*.prompt.md` | GitHub Copilot specification | Slash-command shortcuts |
| `.github/agents/*.md` | Location per specification; `.agent.md` suffix is a project convention | The specification requires only that the file reside in `.github/agents/`; the `.agent.md` suffix is applied by this workflow for readability and is not required by GitHub Copilot |
| `.github/skills/<name>/SKILL.md` | GitHub Copilot specification | Also valid under `.claude/skills/` or `.agents/skills/`; this workflow does not write to either location |
| `.github/hooks/*.json` | GitHub Copilot specification | This workflow consolidates all hooks into a single `guards.json`; the specification also permits multiple hook files |
| `specs/<bug\|feature>/<ticket-id>/` | Project-specific convention | Not a GitHub Copilot concept; the path is computed deterministically (never asked about) and honored by `qatalyst-bug-planner`, `qatalyst-feature-planner`, and `qatalyst-log-analyser` |
| `specs/.templates/*-template.md` | Project-specific convention | The `-template` suffix excludes the scaffold from any glob that scans `specs/**/tasks.md` for live ticket specs, while the `.md` extension preserves Markdown rendering in editors and previews |
| `jira_projects` settings-block field (and its per-entry `key`/`bug_issue_types`) | Project-specific convention | Not a GitHub Copilot concept; read by `qatalyst-ticket-start` at the start of every ticket |

**Implication.** A path classified as GitHub Copilot specification is governed by GitHub's
published behavior and remains valid for as long as that specification does. A path classified as a
project-specific convention carries no external enforcement — it functions only because every
agent and skill that reads or writes it has been written to honor it consistently. Any change to
the `specs/` layout or the `-template.md` convention must therefore be mirrored across all of them.
