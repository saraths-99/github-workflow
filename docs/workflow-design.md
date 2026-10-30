# Agentic AI-SDLC workflow — implementation reference

Internal design reference for this builder repo. Describes what the generated workflow actually
implements: the setup wizard, the daily ticket pipeline, the log-analysis loop, the safety
mechanisms wrapping all of it, and — in §11 — exactly where every file lives, both in this builder
repo and in a generated app repo. Each skill's own `SKILL.md` is the authoritative source — this
document is a synthesis for a single-page view, not a replacement.

## 1. System map

| Place | Holds |
|---|---|
| **Builder repo** (this repo) | The `setup-*` skills and their blueprints — the source for everything below |
| **App repo** | Generated instructions, agents, skills, prompts, hooks, MCP config; the ticket specs |
| **Developer machine** | Filled-in `mcp.json` with a real Atlassian token; optional Repowise index |

Nothing in this repo runs against product code directly. `bootstrap.sh`/`bootstrap.ps1` copies the
`setup-*` skills into an app repo; `/setup-workflow`, run there, generates everything else.

## 2. Setup phase (once per repo)

```mermaid
flowchart TD
    A([Run /setup-workflow]) --> B{Settings block exists?}
    B -- yes --> C["Read jira_projects (key +<br/>bug_issue_types each), base_branch"]
    B -- no --> E
    C --> E[Read code + context docs]
    E --> F{Context docs missing?}
    F -- yes --> G[setup-context-docs drafts docs]
    G --> H[Developer approves draft]
    H --> I
    F -- no --> I[Ask only what code can't show]
    I --> J[Show brief to developer]
    J -- changes requested --> I
    J -- approved --> K["Generate, fixed order:<br/>instructions -> agents -> skills -> hooks -> mcp -> ticket-flow"]
    K --> L[Verify: diff + approve each overwrite]
    L --> M([Hand off: commit, MCP token, Repowise])
```

## 3. Daily ticket workflow (spec-driven development)

Three phases happen in sequence per ticket: **detect & spec**, **implement & test** (looped per
task), **review & ship**. Nothing in phase 2 starts before `tasks.md` is approved in phase 1;
nothing in phase 3 starts before every task is ticked in phase 2.

```mermaid
flowchart TD
    A([/ticket-start ticket]) --> B0{Ticket's project key<br/>matches a configured<br/>jira_projects entry?}
    B0 -- no --> FC[Stop, ask developer]
    B0 -- yes --> B{Issue type in that<br/>project's bug_issue_types?}
    B -- yes, unanalyzed --> C[log-analyser loop, see §4]
    C --> D[log-analysis.md]
    B -- yes, already analyzed --> D
    D --> FA[Reuse feature folder<br/>from log-analysis.md]
    B -- no --> FB[Ask developer<br/>which feature folder]
    FA --> E[ticket-analyst: requirements.md]
    FB --> E
    E --> F{Approved?}
    F -- no --> E
    F -- yes --> G[architect: design.md]
    G --> H{Approved?}
    H -- no --> G
    H -- yes --> I[architect: tasks.md]
    I --> J{Approved?}
    J -- no --> I
    J -- yes --> K[Create feature branches]
    K --> L[developer: implement next task]
    L --> DM{Design mismatch<br/>vs. design.md?}
    DM -- yes --> DR[architect updates<br/>design.md + tasks.md]
    DR --> DAP{Approved?}
    DAP -- no --> DR
    DAP -- yes --> L
    DM -- no --> M[test-writer: write test]
    M --> N{Passes + meets<br/>acceptance criteria?}
    N -- no --> L
    N -- yes --> O[Tick task]
    O --> P{All tasks ticked?}
    P -- no --> L
    P -- yes --> Q[code-reviewer reviews diff]
    Q --> R{Touches sensitive area?}
    R -- yes --> S[security-reviewer reviews diff]
    R -- no --> T
    S --> T{Open comments?}
    T -- yes --> L
    T -- no --> U[Local build + tests]
    U --> V[Ask once: show PR plan]
    V --> W[Push + open PR per repo, merge order]
    W --> X{Pipelines on<br/>for this repo?}
    X -- yes --> Y[Wait for Pipelines pass]
    X -- no --> Z[Note: no pipeline ran]
    Y --> AA([Move ticket to In Review])
    Z --> AA
```

## 4. Log-analysis loop (bug tickets only)

```mermaid
flowchart TD
    A([Intake: read ticket + comments,<br/>pin issue time]) --> X[Extract: logcat_extract.py<br/>.txt passthrough / .zip merge]
    X --> B[Trim: logcat_trim.py]
    B --> C[Digest: logcat_digest.py]
    C --> D[Link: group + match log-signatures.md]
    D --> E[Map: Repowise class/module lookup]
    E --> F[Rank: root-cause hypotheses]
    F --> G{One cause explains<br/>every error?}
    G -- yes --> H([Report: log-analysis.md<br/>+ suggested fix + Jira comment])
    G -- no, pass < 3 --> I[Refine: widen window /<br/>restore noise tag / read code]
    I --> B
    G -- no, pass = 3 --> H
```

Three scripts in this loop are plain Python, no AI, no network:
[`logcat_extract.py`](../.github/skills/setup-agents/assets/log-analyser/scripts/logcat_extract.py)
normalizes the raw attachment (a plain `.txt`/`.log` passes through unchanged; a `.zip` is extracted
and, if it holds more than one text log, merged in chronological order) into the single file
[`logcat_trim.py`](../.github/skills/setup-agents/assets/log-analyser/scripts/logcat_trim.py) expects,
and [`logcat_digest.py`](../.github/skills/setup-agents/assets/log-analyser/scripts/logcat_digest.py)
groups that trimmed log's warnings and errors by signature.

## 5. Agents

| Agent | Job | Tools | MCP | Hard scope rule |
|---|---|---|---|---|
| `log-analyser` | Root-causes a bug ticket's logs with a suggested fix | read, edit, search, runCommands (scripts only) | atlassian-rovo, repowise | Writes only `log-analysis.md`; runs only the three log scripts, in order |
| `ticket-analyst` | Writes `requirements.md` | read, edit, search | atlassian-rovo, figma, repowise | Writes only `requirements.md` |
| `architect` | Writes `design.md`, `tasks.md` | read, edit, search | repowise | Writes only those two files; no new architectural layer |
| `developer` | Implements `tasks.md` | read, edit, search, runCommands | repowise | One task at a time, in order, only via the named skill |
| `test-writer` | Tests each task | read, edit, search, runCommands | repowise | Edits only test files for the in-progress task |
| `code-reviewer` | Reviews diff vs. spec | read, search | repowise | Read-only; checks the specs-only rule on every diff |
| `security-reviewer` | Reviews sensitive-area diffs | read, search | repowise | Read-only; only runs when flagged by `code-reviewer` |

Tool lists are the *mechanical* half of scope enforcement (Copilot can strip `edit` outright); the
*written* half — "only these files," "only these commands" — lives in each agent's own blueprint.
`code-reviewer` is the backstop that actually checks the written half was followed.

## 6. Skills

| Layer | Skills |
|---|---|
| **Builder** (run once, at setup) | `setup-workflow`, `setup-context-docs`, `setup-instructions`, `setup-agents`, `setup-skills`, `setup-hooks`, `setup-mcp`, `setup-ticket-flow` |
| **Project — orchestration** | `ticket-start`, `ticket-ship` |
| **Project — implementation** | `new-feature`, `new-screen`, `new-ble-command`, `new-api-call`, `room-migration`, `write-tests` |

`new-ble-command` and `room-migration` are only generated when BLE or Room is actually detected in
the app repo; the rest are always generated.

## 7. Hooks

| Hook | Event | Denies / does |
|---|---|---|
| `format-kotlin` | `postToolUse` | Runs the formatter on an edited `.kt`/`.kts` file (never denies — event fires after the fact) |
| `block-force-push` | `preToolUse` | Denies a shell command containing `git push` + `--force`/`--force-with-lease`/`-f` |
| `protect-secrets` | `preToolUse` | Denies reads/edits/commands naming a `sensitive-paths.txt` entry; denies text containing a JWT or token-shaped string |
| `guard-context-docs` | `preToolUse` | Asks before `project-context.md`/`architecture.md` is touched; `ask` degrades to `deny` if the agent mode can't ask |

Protocol: each script reads one JSON object on stdin (`event`, `tool`, `paths`, `command`, `text`)
and writes one JSON decision (`allow` / `deny` / `ask`) to stdout. A non-zero exit or a 30-second
timeout both fall back — a crash denies the action, a timeout silently allows it (see
[`hook-protocol.md`](../.github/skills/setup-hooks/references/hook-protocol.md) and open item 4 in §10).

## 8. MCP servers

| Server | Used for | Auth |
|---|---|---|
| Atlassian Rovo MCP | Jira, Confluence, Bitbucket Cloud | OAuth (Jira/Confluence); Basic auth API token (Bitbucket) |
| Figma MCP | Linked designs, read-only | Developer's Figma sign-in |
| Repowise | Code map, risk, dead-code (advisory only) | None — local, optional |

## 9. Safety & control principles

- **Developer approves every gate** — the setup brief, each spec file, every overwrite, and the
  commit/push/PR step all wait for an explicit yes.
- **Spec before code** — no feature branch exists until `tasks.md` is approved; `developer` can't
  start a task the spec doesn't list.
- **Context docs are read, not guessed** — drafted only when missing, cited line-by-line, never
  regenerated once written.
- **Redact before sharing** — raw logs stay in a git-ignored `.logs/` folder; everything else sees
  only trimmed/digested/redacted output.
- **Mechanical enforcement where possible, written rules elsewhere** — reviewers lose the `edit`
  tool outright; path-scoping ("specs only," "scripts only") is a written rule, checked by
  `code-reviewer`.
- **No secrets in the repo** — both MCP files ship with an empty token slot; `protect-secrets`
  blocks the paths that would leak one.

## 10. Known gaps / open risk items

Found by audit, not yet closed — listed here so they stay visible rather than living only in chat:

1. **Test/spec gaming under pressure** — nothing stops `test-writer` from weakening an assertion,
   or `architect`'s "plan changed" re-approval path from being used to dodge a hard bug rather than
   fix it.
2. **UI error/loading/empty states** — `new-screen` and `xml-ui.instructions.md` stop at wiring;
   nothing requires a screen to handle or test a failure/loading/empty state.
3. **No retry cap for `developer`/`test-writer`** — unlike `log-analyser`'s 3-pass cap, nothing
   says "stop and report" after N failed attempts at a task.
4. **Silent hook degradation** — a timed-out guard "falls back to normal permissions" with no
   requirement that the agent notice or disclose it.
5. **Multi-repo partial failure in `ticket-ship`** — no defined behavior if repo 2's push/PR fails
   after repo 1 succeeded, or if a Pipelines run actually fails rather than just being pending.
6. **"Resolved" is undefined** for review comments — unclear if a developer override counts.
7. **Ticket reclassified after `ticket-start` runs** — issue type is read once; a later
   feature→bug (or reverse) reclassification isn't re-checked.
8. **Technically-passing-but-wrong-approach implementations** — `code-reviewer` checks criteria are
   met, not that the approach matches `design.md`'s intent.
9. **Flaky test passes** — the gate is "passed locally, once"; no rule addresses intermittent tests.
10. **Branch/feature-folder collisions** — no rule for two tickets proposing the same slug.

## 11. Folder structure

Where every file lives, in the builder repo and in a generated app repo, and which of those paths
are a real GitHub Copilot standard versus a convention this workflow invented for itself.

### 11.1 Builder repo (this repo)

```
github-workflow/
├── README.md
├── bootstrap.sh / bootstrap.ps1
├── docs/
│   └── workflow-design.md            (this file — design reference + folder structure)
├── tests/
│   └── static_checks.py
└── .github/
    ├── copilot-instructions.md       rules for working on this builder repo itself
    ├── agents/                       (placeholder — optional org-level agent, not built)
    ├── prompts/setup-workflow.prompt.md
    └── skills/
        ├── setup-workflow/           entry point — the wizard
        │   ├── SKILL.md
        │   └── references/  (detection-rules.md, question-bank.md)
        ├── setup-context-docs/
        │   ├── SKILL.md
        │   ├── references/field-sources.md
        │   └── assets/  (project-context-template.md, architecture-template.md)
        ├── setup-instructions/
        │   ├── SKILL.md
        │   ├── references/detection-map.md
        │   └── assets/  (copilot-instructions-template.md + 8 *.instructions.md)
        ├── setup-agents/
        │   ├── SKILL.md
        │   ├── references/tool-lists.md
        │   └── assets/
        │       ├── agents/        (7 × *.agent.md)
        │       ├── prompts/log-analyser.prompt.md
        │       └── log-analyser/  (logcat_extract.py, logcat_trim.py, logcat_digest.py, log-signatures-template.md)
        ├── setup-skills/
        │   ├── SKILL.md
        │   ├── references/detection-map.md
        │   └── assets/
        │       ├── skills/   (new-feature, new-screen, new-ble-command, new-api-call, room-migration, write-tests)
        │       └── prompts/  (6 matching .prompt.md)
        ├── setup-hooks/
        │   ├── SKILL.md
        │   ├── references/  (hook-protocol.md, seeding-rules.md)
        │   └── assets/  (guards.json, sensitive-paths.txt, scripts/ × 4 hooks × .sh+.ps1)
        ├── setup-mcp/
        │   ├── SKILL.md
        │   ├── references/tool-check.md
        │   └── assets/  (mcp.json, mcp/jetbrains-mcp.example.json)
        └── setup-ticket-flow/
            ├── SKILL.md
            ├── references/pipelines-detection.md
            └── assets/
                ├── skills/ticket-start, skills/ticket-ship
                ├── prompts/ (2 matching .prompt.md)
                └── spec-templates/ (requirements-template.md, design-template.md, tasks-template.md)
```

Every blueprint lives under its owning `setup-*` skill's own `assets/`. Nothing is shared across
skill folders — a cross-cutting concern gets a `references/*.md` file inside whichever skill owns
it most, linked to from the others, rather than a top-level shared folder (see §11.4).

### 11.2 Generated app repo (after `/setup-workflow`'s first run)

Assumes the full target stack (both BLE stacks, Room, AppSync all detected — see §11.2.1 for what's
conditional).

```
<app-repo>/
├── project-context.md                 drafted by setup-context-docs if missing; never regenerated
├── architecture.md                    same
├── workflow.prompt.md                 pre-existing — linked, never written by this workflow
├── docs/workflows/                    pre-existing — same
├── .gitignore                         .logs/ appended by setup-agents (file created if missing)
├── specs/
│   └── .templates/
│       ├── requirements-template.md
│       ├── design-template.md
│       └── tasks-template.md          scaffolds only — see §11.4 for the -template.md convention
├── .logs/                             created lazily, git-ignored — see §11.3
└── .github/
    ├── copilot-instructions.md        settings block + module map + key rules + links
    ├── instructions/                  8 files, conditional — see §11.2.1
    │   ├── kotlin.instructions.md
    │   ├── xml-ui.instructions.md
    │   ├── koin-di.instructions.md
    │   ├── ble-halo.instructions.md
    │   ├── ble-gdo.instructions.md
    │   ├── data-layer.instructions.md
    │   ├── testing.instructions.md
    │   └── gradle.instructions.md
    ├── agents/                        all 7 always generated
    │   ├── log-analyser.agent.md
    │   ├── ticket-analyst.agent.md
    │   ├── architect.agent.md
    │   ├── developer.agent.md
    │   ├── test-writer.agent.md
    │   ├── code-reviewer.agent.md
    │   └── security-reviewer.agent.md
    ├── log-analyser/
    │   ├── scripts/logcat_extract.py
    │   ├── scripts/logcat_trim.py
    │   ├── scripts/logcat_digest.py
    │   └── log-signatures.md
    ├── skills/
    │   ├── new-feature/SKILL.md
    │   ├── new-screen/SKILL.md
    │   ├── new-ble-command/SKILL.md   conditional — see §11.2.1
    │   ├── new-api-call/SKILL.md
    │   ├── room-migration/SKILL.md    conditional — see §11.2.1
    │   ├── write-tests/SKILL.md
    │   ├── ticket-start/SKILL.md
    │   ├── ticket-ship/SKILL.md
    │   └── setup-*/                   retained — see §11.2.2
    ├── prompts/
    │   ├── setup-workflow.prompt.md   kept — the re-run entry point
    │   ├── log-analyser.prompt.md
    │   ├── new-feature.prompt.md
    │   ├── new-screen.prompt.md
    │   ├── new-ble-command.prompt.md
    │   ├── new-api-call.prompt.md
    │   ├── room-migration.prompt.md
    │   ├── write-tests.prompt.md
    │   ├── ticket-start.prompt.md
    │   └── ticket-ship.prompt.md
    ├── hooks/
    │   ├── guards.json
    │   ├── sensitive-paths.txt
    │   └── scripts/  (format-kotlin, block-force-push, protect-secrets, guard-context-docs — each .sh + .ps1)
    ├── mcp/jetbrains-mcp.example.json
    └── mcp.json
```

#### 11.2.1 Conditional pieces

Gated on what `setup-workflow`'s Read step actually detects — absent entirely for a repo that
doesn't match the signal, never generated as an empty placeholder:

| File(s) | Generated when |
|---|---|
| `ble-halo.instructions.md`, `ble-gdo.instructions.md`, `new-ble-command/` | that BLE stack is detected |
| `room-migration/` | Room (`@Database`) is detected |
| `koin-di.instructions.md` | Koin is detected |
| `xml-ui.instructions.md`, `new-screen/` | XML + View Binding is detected |

Everything else (`kotlin.instructions.md`, `testing.instructions.md`, `gradle.instructions.md`,
all 7 agents, `new-feature`, `write-tests`, `ticket-start`, `ticket-ship`) is always generated.

#### 11.2.2 `.github/skills/setup-*/` is retained, not deleted

No `SKILL.md` deletes the `setup-*` skills after generation. This is deliberate: `setup-workflow`
is re-run-safe (it reads the settings block and re-detects the stack), so a later re-run — new BLE
stack added, architecture changed — needs those skills still present. The original design doc's own
app-repo tree omits them (focused on the generated output, not the machinery that produced it), but
nothing in this workflow currently cleans them up. Decide explicitly if that should change.

### 11.3 Per-ticket runtime additions

Not present until a ticket is actually worked; one set per ticket, inside its feature folder.

```
specs/<feature>/<ticket-id>/
├── log-analysis.md      bug tickets only — written by log-analyser
├── requirements.md      written by ticket-analyst
├── design.md             written by architect
└── tasks.md              written by architect

.logs/<ticket-id>/
├── raw/                 as captured (.txt/.log, or a .zip) — protect-secrets hook blocks Copilot reads
│   └── extracted/        logcat_extract.py's output — same hook applies, still the full raw log
├── trimmed.log           redacted + windowed — what log-analyser actually reads
└── digest.md             error groups with counts and first/last times
```

### 11.4 Naming conventions: specification compliance

Every path under `.github/` conforms to a documented GitHub Copilot customization path, verified
against the [customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet).
Every path outside `.github/` — `specs/`, the `-template.md` suffix, the `generated-by` marker — is
a project-specific convention introduced by this workflow; GitHub Copilot has no knowledge of it and
assigns it no behavior.

| Path / suffix | Classification | Notes |
|---|---|---|
| `.github/copilot-instructions.md` | GitHub Copilot specification | Repository-wide instructions |
| `.github/instructions/*.instructions.md` | GitHub Copilot specification | Path-specific instructions; requires an `applyTo` front-matter field |
| `.github/prompts/*.prompt.md` | GitHub Copilot specification | Slash-command shortcuts |
| `.github/agents/*.md` | Location per specification; `.agent.md` suffix is a project convention | The specification requires only that the file reside in `.github/agents/`; the `.agent.md` suffix is applied by this workflow for readability and is not required by GitHub Copilot |
| `.github/skills/<name>/SKILL.md` | GitHub Copilot specification | Also valid under `.claude/skills/` or `.agents/skills/`; this workflow does not write to either location |
| `.github/hooks/*.json` | GitHub Copilot specification | This workflow consolidates all hooks into a single `guards.json`; the specification also permits multiple hook files |
| `~/.copilot/skills/` | GitHub Copilot specification (user scope) | A per-user, home-directory skill location; `bootstrap.sh` does not write to it |
| `specs/<feature>/<ticket-id>/` | Project-specific convention | Not a GitHub Copilot concept; the path is defined and honored by `ticket-analyst`, `architect`, and `log-analyser` |
| `specs/.templates/*-template.md` | Project-specific convention | The `-template` suffix excludes blueprint files from any glob that scans `specs/**/requirements.md` for live ticket specs, while the `.md` extension preserves Markdown rendering in editors and previews |
| `*-template.md` elsewhere (`copilot-instructions-template.md`, `project-context-template.md`, …) | Project-specific convention | Applied for the same reason, consistently, across every generated-file blueprint in this builder repo |
| `generated-by: copilot-workflow` marker | Project-specific convention | Distinguishes files written by `setup-workflow` from developer-authored files on a re-run |
| `bug_issue_types` settings-block field | Project-specific convention | Not a GitHub Copilot concept; part of this workflow's own re-run contract |

**Implication.** A path classified as GitHub Copilot specification is governed by GitHub's
published behavior and remains valid for as long as that specification does. A path classified as a
project-specific convention carries no external enforcement — it functions only because every skill
in this builder repo has been written to honor it consistently. Any change to the `specs/` layout
or the `-template.md` convention must therefore be mirrored across every skill that reads or writes
it.
