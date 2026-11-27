# Agentic AI-SDLC workflow — implementation reference

Design reference for what actually runs inside this repo: the daily ticket pipeline, the
log-analysis loop, the safety mechanisms wrapping all of it, and — in §10 — exactly where every one
of those files lives. Each skill's own `SKILL.md` is the authoritative source for its own
behavior — this document is a synthesis for a single-page view, not a replacement.

This workflow's files are edited directly, in place — there's no wizard, no templating, no
detection logic. The one remaining moving part is `install.sh` (see
[README.md §2](../README.md#2-one-time-setup)): a plain file sync, run from inside the actual app
repo, that pulls the latest agents/skills/instructions/prompts/mcp config from this repo and
overwrites them there — a one-way copy, not a generator run against detected app-repo state.

## 1. One-time manual fill-ins

Three things can't be read off the code or guessed, so `install.sh` never overwrites
them once they exist — they're filled in once by hand instead:

- `copilot-instructions.md`'s settings block (`jira_projects`, `base_branch`), module map, and key
  rules.
- `project-context.md` and `architecture.md`, drafted from the real code per
  [`docs/field-sources.md`](https://github.com/saraths-99/github-workflow/blob/develop/docs/field-sources.md), confirmed by a developer, then never regenerated —
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
    G --> H[Write the commit message,<br/>build and test]
    H --> I([Commit locally —<br/>you push and open the PR])
```

When the evidence points outside the app (firmware, backend or an SDK) on a ticket that isn't Android only, `qatalyst-log-analyser`
records an "Outside the app" section and `qatalyst-plan-ticket` turns it into `.logs/<ticket ID>/outside-app-note.md`: a note for
that team with the evidence, the app's command sequence, expected against actual, a specific ask, the app's workaround and the
unknowns, using only facts from the ticket, log and code and no secrets or device identifiers. It is copied into `no-fix.md` and the
workflow report and is never sent by the workflow.

A ticket whose QA note says the issue is not observed on iOS is treated as Android only:
`qatalyst-jira-ticket-intake` reports the platform scope, `qatalyst-log-analyser` ranks causes in the
app and platform and suggests only an app fix, and `qatalyst-plan-ticket` plans no firmware or
cloud/backend change (those stay in the report's related areas as "not a fix target"). An unclear or
contradictory ticket is "not stated" and nothing changes.

The Plan box is one agent, one file, one approval: `qatalyst-bug-planner` for a bug ticket (after
the
log-analysis loop), `qatalyst-feature-planner` otherwise. Earlier versions of this workflow split
Plan into
three separate files and three separate approvals (requirements, then design, then tasks) written
by two different agents — that meant asking the developer to approve three times, and a duplicate
ask for the feature folder name along the way (one agent resolved it, the next one re-confirmed
it). `tasks.md` now carries what the old `requirements.md` and `design.md` covered — what the ticket
is for, acceptance criteria, edge cases, approach/risks — as sections ahead of the task checklist, in
the single file `qatalyst-code-reviewer` and `qatalyst-test-writer` check against. For a bug, the first
acceptance criterion is the reported scenario itself, so the fix is planned with a test that
reproduces it; each edge case is tied to the task whose test covers it. The approval also asks whether
to write tests at all: "No tests for this ticket" sets `**Tests:** none` in `tasks.md`, which
`qatalyst-developer`, `qatalyst-code-reviewer` and `qatalyst-ticket-ship` all read (no test-writer
hand-off, no missing-test comments, and a line in each commit message saying none were written).

The flow ends at a local commit. `qatalyst-ticket-ship` never pushes, opens a pull request, reads a
Pipelines run or moves the ticket; the developer pushes the branch and opens the PR. That keeps the
Bitbucket side (API token, admin-enabled tools) out of this workflow entirely.

### Workflow report

When every task is ticked, `qatalyst-developer` follows `qatalyst-repowise-lookup`'s "Workflow
report" steps and writes `.logs/<ticket ID>/workflow-report.md`. For a bug it starts with how many of
the 5 allowed analysis passes it took to reach a confident fix (copied from `log-analysis.md`'s
"Analysis passes" section, one line per pass and how it ended). It then covers the blast radius: the
files and symbols the ticket changed, their dependents in every repo of the workspace, the change risk, the tests around the
change, and whether each changed file is current in Repowise's index. A "Related areas that could affect the fix" section lists
what sits outside the changed code (lock firmware and the model numbers that reach it, the other BLE stack, the backend, the
platform, third-party and sibling modules), each with evidence and a check, and never states firmware or backend behaviour
the code, docs, ticket or log don't support. It tells the developer in chat
whether the index was used (every lookup, some, or none and why) and names any stale files. Without
Repowise it still writes the report from direct searches and marks every row as such. `qatalyst-ticket-start` then shows the whole report in chat under its full path, in every IDE, and the
commit step shows the summary in its confirmation. A "Workflow checks" section records, self-reported by the
agent, how the token report went (written, off, no hand-off received, or failed with the reason),
which hand-off it received, and the Repowise index and commit hook status; anything it wasn't told is
"not recorded". The token report step therefore runs before the workflow report. The report covers only its own lookups and the
ticket-start status, not lookups made earlier by the planners or the log analyser.

### Token usage per ticket (Beta — works in VS Code)

This feature is in beta and runs in VS Code only. `qatalyst-ticket-start` checks which IDE it is in
(VS Code has the `vscode/askQuestions` tool), runs `mark` only there, and tells the agents it hands
off to "Token tracking: on" or "off"; `qatalyst-developer` writes the report only when told "on", and `qatalyst-ticket-ship` writes it again, and shows it, once the review is done.
Elsewhere nothing is created.

`.github/token-tracker/scripts/token_tracker.py` reports how many tokens a ticket used, one row per
model call: `ticketId`, `agentName`, `model`, `inputTokens`, `outputTokens`, `timestamp`, plus a
summary by agent and by model. It reads only what Copilot itself records locally; nothing is sent
anywhere, and prompt or code content is never captured.

| Where the developer works | Trace source | What's available |
|---|---|---|
| VS Code Copilot Chat | `agent-traces.db` in VS Code's storage for the Copilot Chat extension, turned on by `github.copilot.chat.otel.dbSpanExporter.enabled` | every model call, by agent and sub-agent |

- **Turning it on in VS Code.** The setting isn't listed in the Settings screen, so searching for it
  there finds nothing; it goes in a settings JSON file. VS Code reads it from only two places: the
  app repo's own `.vscode/settings.json` (the folder open in VS Code, not this workflow repo), or
  the user settings (**Preferences: Open User Settings (JSON)**). `.github/token-tracker/vscode-settings.json`
  is only the template `install.sh` copies into a new `.vscode/settings.json`; editing it changes
  nothing. Add `"github.copilot.chat.otel.dbSpanExporter.enabled": true`, run **Developer: Reload
  Window**, send one chat message, and check that `agent-traces.db` now exists
  (`~/.config/Code/User/globalStorage/github.copilot-chat/` on Linux,
  `~/Library/Application Support/Code/User/globalStorage/github.copilot-chat/` on macOS). If the
  setting shows "Unknown configuration setting", the installed Copilot Chat extension is too old to
  have it. The file is only created once the setting is on and the window reloaded, so chats held
  before then are never recorded and a ticket worked earlier reports 0 model calls.

- **Linking chats to a ticket.** Copilot's traces don't contain a ticket ID. A chat is linked when
  `token_tracker.py mark <ticket ID>` runs during it (`qatalyst-ticket-start` does this first, in
  VS Code only), or, failing that, when any turn in it ran on a branch named
  for the ticket. The `qatalyst-ticket` picker agent has no terminal tool, so its chats rely on the
  branch rule.
- **Agent names.** An agent picked from the picker is recorded by Copilot as "GitHub Copilot Chat"
  with its own name in a separate attribute; the tracker uses that name. A chat with no custom agent
  shows as "GitHub Copilot Chat".
- **Skills** make no model calls of their own, so they have no rows: a skill's text is
  counted in the input tokens of the agent that loaded it.
- **Retention.** Copilot deletes its own trace rows after 7 days, so every `collect`/`report` run
  copies new calls into `.logs/token-tracker/calls.jsonl` (git-ignored), and reports are built from
  that copy. Calls recorded against a different repo's remote URL are skipped.
- **Why not Copilot's `file` exporter in VS Code.** As of Copilot Chat's current source, its file
  exporter serializes span objects directly, which fails on a circular reference and writes `{}`
  for every span (reproduced with OpenTelemetry SDK 2.5.1 and 2.12.1). The SQLite store converts
  spans to plain rows first and doesn't have this problem.

`qatalyst-developer` runs `token_tracker.py report <ticket ID>` once every task in
`tasks.md` is ticked, so the workflow report can record the outcome, and `qatalyst-ticket-ship` runs
it again with `--open` once the review is done, so the figures shown cover the review fixes too; a developer can run
it again any time, for example after the commit to include the build, tests and commit steps. Output goes to `.logs/token-tracker/<ticket ID>/`:
`token-usage.html` (a self-contained page with no scripts, opened in the browser by `--open` where
there's a local display) and `token-usage.json` (ticket, executor and total cost, then `steps` by agent, each with its
calls: fresh, cached and cache-write input tokens, output tokens and cost). Both come from the same data.
Copilot's trace carries three things per call that the tracker now reads: `gen_ai.usage.cache_read.input_tokens`,
`gen_ai.usage.cache_creation.input_tokens` and `copilot_chat.copilot_usage_nano_aiu`, its own cost in billionths of
an AI credit (1 credit = $0.01). The recorded input includes the cache read and write tokens (checked on real
calls), so `inputTokens` in the JSON is input minus those two. The cost is Copilot's figure, which reproduces the
price sheet exactly for Claude and Codex calls; calls with none fall back to a price sheet when one is given
(input beyond the cache reads is billed at the sheet's Cache write rate for OpenAI models that report no
explicit write, and GPT-6 Luna was billed 10% under the sheet, so the fallback is an estimate).

## 3. Log-analysis loop (bug tickets only)

```mermaid
flowchart TD
    A([Intake: read ticket + every<br/>comment, pin issue time]) --> W[Fetch: download the attached log<br/>into .logs/ticket-id/raw/]
    W --> X[Extract: logcat_extract.py<br/>.txt passthrough / .zip merge]
    X --> B[Trim: logcat_trim.py]
    B --> BW{Trimmed to ~0 lines?}
    BW -- yes --> BWX([Stop: ask developer —<br/>wrong file or window, not actually clean])
    BW -- no --> C[Digest: logcat_digest.py]
    C --> CW{Any warnings<br/>or errors?}
    CW -- no --> CWX([Ask developer: widen window,<br/>whole log, report inconclusive, or stop])
    CW -- yes --> D[Link: group related entries]
    D --> E[Map: Repowise class/module lookup]
    E --> CX[Context: logcat_context.py —<br/>what the trimmed log left out]
    CX --> F[Rank: root-cause hypotheses]
    F --> G{One cause explains<br/>every error?}
    G -- yes --> H([Report: log-analysis.md<br/>+ suggested fix])
    G -- no, pass < 5 --> I[Refine: widen window / restore noise tag /<br/>other Context tags / read code]
    I --> B
    G -- no, pass = 5 --> H
```

If the ticket has a log but gives no time for the issue, Intake asks the developer for one instead of
guessing: a time of day, the whole log with no time window, or stop until the ticket has it.

A log attached to the ticket (rather than pasted in a comment) is downloaded by `qatalyst-log-analyser`
through the Atlassian server's `downloadJiraIssueAttachment` operation, into `.logs/<ticket ID>/raw/`.
If the download can't run, the developer is told which step failed and
which file name to save the log as.

Four scripts in this loop are plain Python, no AI, no network: `logcat_extract.py` normalizes the
raw attachment (a plain `.txt`/`.log` passes through unchanged; a `.zip` is extracted and, if it
holds more than one text log, merged in chronological order) into the single file `logcat_trim.py`
expects, `logcat_digest.py` groups that trimmed log's warnings and errors by signature, and
`logcat_context.py` goes back to the full log for what those two leave out.

**Why Context exists.** `logcat_trim.py` keeps only the app's own process, a window of 120 s before and
30 s after the issue time, and drops `BluetoothLeScanner`, `bt_btm` and the `BtGatt.*` tags unless a line is an
error; the digest then keeps only warnings and errors. That finds the app's errors and hides the things that
explain them: the Bluetooth stack's own connection state and disconnect reason (another process, a noise
tag), the app's commands before the failure, the process dying or being restarted, whether the same error had
been firing for an hour, the app, phone, Android and firmware versions, and whether the log even covers the
failure. `logcat_context.py` reads the extracted log again with the same redaction and returns those as one
capped report (150 lines per section, the nearest the issue time kept): log boundaries and gaps, environment
lines, process lifecycle, a lead-up window of every level from every process for the given tags and patterns,
and per-minute counts over the whole log. It runs between Map and Rank, and again in Refine with other tags;
`log-analysis.md` gets a "Context checked" section. Its environment and lifecycle matching uses fixed
patterns, so finding nothing there is not proof that nothing is in the log. It is the one place besides
`logcat_trim.py` that reads the raw log, and the analyser still never does.

## 4. Agents

Every workspace agent uses the VS Code Copilot custom-agent schema: `.agent.md` under
`.github/agents/`, `target: github-copilot`, supported tool aliases (`execute`, not
`runCommands`), and configured MCP namespaces in `tools` (for example `repowise/*`). These agents
are workflow workers, so `user-invocable: false` hides them from the picker while keeping
model-driven delegation enabled. Agents that delegate include the `agent` tool; agents that use a
repo skill list it in `skills`. The portable server definitions live in the workspace-root
`.mcp.json`.

Each agent's `tools` also lists the names Android Studio's Copilot registers its tools under, after
the VS Code groups they correspond to: `read` → `read_file`, `list_dir`, `get_errors`; `search` →
`grep_search`, `file_search`, `semantic_search`; `edit` → `insert_edit_into_file`, `create_file`;
`execute` → `run_in_terminal`, `get_terminal_output`. Each IDE ignores the names it doesn't know.
Without them, a sub-agent started in Android Studio can come up with no tools, and the agent that
started it does the work itself instead ("the subagent sandbox doesn't have access to this
workspace's tools"). Android Studio's name for the `agent` (sub-agent) tool isn't known yet, so
delegation there still depends on `agent` being recognised; `x-github-copilot-invoke-policy` mirrors
`user-invocable` for its picker.

**Model tiers.** An agent's `model:` frontmatter pins its model, as a list of
`<name> (copilot)` entries tried in order; an agent without one runs on the model of whatever started
it.

| Tier | Claude, in order | GPT, in order | Agents |
|---|---|---|---|
| Deep | Sonnet 5.5 | GPT-5.6 Sol → GPT-6.1 Sol | Set by `qatalyst-ticket` and the `/qatalyst-ticket-start`, `/log-analyser` and `/qatalyst-ticket-ship` prompts; pinned on `qatalyst-log-analyser`, `qatalyst-code-reviewer` and `qatalyst-developer`. Unpinned, so they run on the chat's model: `qatalyst-bug-planner`, `qatalyst-feature-planner` |
| Standard | Sonnet 5.5 → Sonnet 5 | GPT-6.1 Sol | `qatalyst-error-handling-reviewer`, `qatalyst-security-reviewer`; also the `/qatalyst-new-*` and `/qatalyst-room-migration` prompts |
| Fast | Haiku 5.5 → Haiku 4.5 | GPT-6 Luna → GPT-5.6 Luna | `qatalyst-log-ticket-intake` and every test writer: the router (`qatalyst-test-writer`) and the unit, BLE-protocol, androidTest, compatibility, security, interop, OTA, performance and chaos writers; also the `/qatalyst-write-tests` prompt |
| Judge | GPT-5.3-Codex | GPT-5.3-Codex | `qatalyst-fix-approver` only: the independent approval before a commit. The one place a Claude install uses a GPT model, so the check isn't the model family that wrote the fix. |
| Judge fallback | GPT-6.1 Terra | GPT-6.1 Terra | `qatalyst-fix-approver-fallback` only, when the judge model is refused as costlier than the chat's |

**One provider throughout.** The developer chooses Claude or GPT when installing (`install.sh
--provider claude|gpt`, or the question it asks on a first install; the choice is kept in
`.github/workflow-sync.md` and reused on later runs). The lists live in `models.json`, and
`set-models.py` copies the chosen provider's list for each tier into every agent's and prompt's
`model:` line in the app repo. The files in this repo carry the Claude lists; `models.json` and
`set-models.py` stay here and aren't installed. Because every agent then runs on one provider's
models, the plan must include that provider's models; there is no fallback to the other vendor. The
choice is per app repo and changes by re-running the install with the other `--provider`. Where an
IDE ignores `model:` (Android Studio isn't confirmed to read it), every agent runs on whichever
model is picked in the chat, so pick one from the same provider.

Each tier stays inside one of Copilot's own categories (Powerful, Versatile, Lightweight) at a
similar token price across the two providers: GPT-6.1 Sol is rated Powerful at $2 in / $10 out per
million tokens, the same price as Sonnet 5.5; GPT-5.6 Sol costs $4 / $20, twice Sonnet 5.5 (the Claude Deep list has no Opus now, so GPT's Deep tier is the pricier of the two); GPT-6 Luna
($0.10 / $0.50) matches Haiku 5.5. GPT-6 Astra ($10 / $50) is left out: it costs 2.5× GPT-5.6 Sol, and a
sub-agent can't run on a costlier model than its chat. Gemini, Grok and MAI-Code aren't listed;
adding a provider means adding a block to `models.json` with the same three tiers.

`qatalyst-fix-approver` is the exception to "one provider throughout" and carries a risk: GPT-5.3-Codex
is priced at $1.75 in / $14 out against Sonnet 5.5's $2 / $10, and Copilot lists it as Powerful against
Sonnet's Versatile. If VS Code counts it as costlier than the chat's model it refuses to start the
approver; `qatalyst-ticket-ship` then runs `qatalyst-fix-approver-fallback`, the same check on GPT-6.1 Terra
($1 / $5, Versatile like Sonnet, cheaper in both directions), and only asks whether to continue without
independent approval if that can't give one either. A model list can't do this on its own, since VS Code
checks the first name only, so the fallback is a second agent. Because an agent whose model isn't in the
developer's picker silently runs on its starter's model, both approvers state their model on the first
line and ship rejects an answer from a Claude model or the chat's own. Whether either starts has to be
checked on a real run.

VS Code refuses to start a sub-agent on a model that costs more than the model of the chat (or
agent) that started it, so cost only ever steps down along a chain: chat → `qatalyst-developer` →
`qatalyst-test-writer` → a test writer. That is why the two planners are left unpinned and the entry
points carry the top pin, and why every prompt that starts a pinned agent pins at least that tier
itself. VS Code checks that rule against the first name it finds, so an entry that costs more than
the chat fails instead of moving on to the next. If none of an agent's names is in a developer's
model picker, the agent falls back to its starter's model. Whether Android Studio's Copilot reads
`model:` isn't known; if it doesn't, every agent there runs on the model picked in the chat.

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
| `qatalyst-fix-approver` | Independent approval before a commit: judges whether the diff really fixes the ticket, on GPT-5.3-Codex | read, search, repowise/* | Read-only; returns `Verdict: APPROVED` or `NOT APPROVED` with numbered findings; the verdict gates `qatalyst-ticket-ship`'s commit |
| `qatalyst-fix-approver-fallback` | The same independent approval on GPT-6.1 Terra ($1 / $5), run only when `qatalyst-fix-approver`'s model is refused as costlier than the chat's | read, search, repowise/* | Read-only; carries no procedure of its own, both use the `qatalyst-fix-approval` skill |
| `qatalyst-bug-planner` | Writes `tasks.md` for a bug ticket, from `log-analysis.md`; mechanics live in the `qatalyst-plan-ticket` skill, including its fix check (already fixed, blocked, or ambiguous: ask whether to produce a fix) | read, edit, search, atlassian-rovo/*, repowise/* | Writes only `tasks.md`, to the same deterministic `specs/bug/<ticket ID>/` path `qatalyst-log-analyser` already used, and `.logs/<ticket ID>/no-fix.md` when the developer picks "Do not produce a fix" |
| `qatalyst-feature-planner` | Writes `tasks.md` for a feature ticket; mechanics live in the `qatalyst-plan-ticket` skill, including its fix check | read, edit, search, atlassian-rovo/*, repowise/* | Writes only `tasks.md`, to the deterministic `specs/feature/<ticket ID>/` path — nothing to resolve or ask about — and `.logs/<ticket ID>/no-fix.md` when the developer picks "Do not produce a fix" |
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
  exists) — the backstop is the developer reviewing `log-analysis.md`.
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
| **Cross-cutting** (shared mechanics, referenced by multiple agents/skills above rather than restated) | `qatalyst-jira-ticket-intake` (reading a Jira ticket in full, with an issue-time-pinning extension), `qatalyst-spec-folder-resolution` (computing the deterministic `specs/<bug\|feature>/<ticket ID>/` path — no listing, no asking), `qatalyst-repowise-lookup` (the Repowise-then-fallback, check-once pattern), `qatalyst-commit-message` (the commit title and message per repo, written from the diff and `tasks.md`, shown with options to rework it, saved to `.logs/<ticket ID>/commit-message.md`; used at ship and when the developer stops to ship later), `qatalyst-ask-developer` (every stop is a question with options — `vscode/askQuestions` in VS Code, `ask_questions` in Android Studio, `ask_user` in the Copilot CLI, numbered options where none exists — never an open-ended prompt), `qatalyst-koin-wiring` (registering a binding in `AppModule.kt`) |

`qatalyst-ticket` is a `user-invocable: true` agent-picker entry point that wraps `qatalyst-ticket-start` with
no procedure of its own — an alternative surface to typing `/qatalyst-ticket-start <ticket ID>`, not a
replacement for it; the two must be kept in sync if `qatalyst-ticket-start`'s flow changes.

## 6. Hooks

This workflow ships no hooks. An earlier version had four guard hooks (a Kotlin formatter, a
force-push block, a secret and sensitive-path guard, and a context-doc guard). They were removed
in 0.4.8, and `install.sh` deletes the copies an older install left in an app repo.

Without them, the guards are the mechanical tool lists (reviewers have no `edit` tool) and the
written rules in each agent and instruction file, checked by `qatalyst-code-reviewer`. Commands and
edits are covered only by Copilot's own approval prompts, so read them before you allow them.

## 7. MCP servers

| Server | Used for | Auth |
|---|---|---|
| Atlassian Rovo MCP | Jira and Confluence (Bitbucket tools aren't used by the workflow) | OAuth (Jira/Confluence) |
| Repowise | Code map, risk, dead-code (advisory only) | None — local, optional |

`/qatalyst-ticket-start` checks Repowise at the start of every ticket. If it isn't ready (not
installed, not indexed, or repos missing or behind), it asks the developer to set it up, continue
without it, or stop, and tells every agent it hands off to the outcome so none re-checks. It never
runs the install or index commands itself. Once Repowise is ready it also checks `repowise hook
status --workspace` and installs the post-commit hook (`repowise hook install <repo>`, never
`--security`) in each repo that lacks it and has no post-commit hook of its own, so the index is
re-built after every commit. This is a local git hook, not one of the Copilot guard hooks removed
from this workflow.

Atlassian is reached at `https://mcp.atlassian.com/v2/mcp` (the `/v1/sse` endpoint was retired on
30 June 2026). Setup and sign-in per IDE, including Android Studio's Local agent, are in the
`.github/workflow-guide.md`, "MCP servers".

## 8. Safety & control principles

- **Developer approves every gate** — each spec file, every task, and the commit step all
  wait for an explicit yes. Nothing is pushed and no PR is opened by the workflow.
- **Spec before code** — no ticket branch exists until `tasks.md` is approved; `qatalyst-developer`
  can't start a task the spec doesn't list.
- **Context docs are read, not guessed** — `project-context.md`/`architecture.md` are drafted once
  from the real code, cited line-by-line, never regenerated once written.
- **Redact before sharing** — raw logs stay in a git-ignored `.logs/` folder; everything else sees
  only trimmed/digested/redacted output.
- **Mechanical enforcement where possible, written rules elsewhere** — reviewers lose the `edit`
  tool outright; path-scoping ("specs only," "scripts only") is a written rule, checked by
  `qatalyst-code-reviewer`.
- **No secrets in the repo** — both MCP files ship with an empty token slot.
- **A model per job** — the ticket chat, log analysis and planning run on the strongest model, since
  a weaker one is more likely to skip an approval gate or misclassify a ticket than to be caught
  doing so; implementation and review run a tier below, and most test writing on a fast model (see
  §4's model tiers and `copilot-instructions.md`'s Model section).

## 9. Known gaps / open risk items

Found by audit, not yet closed — listed here so they stay visible rather than living only in chat:

1. **Test/spec gaming under pressure** — nothing stops `qatalyst-test-writer` from weakening an
   assertion,
   or the "plan changed" re-approval path (`qatalyst-bug-planner`/`qatalyst-feature-planner`) from
   being used to dodge
   a hard bug rather than fix it.
2. **UI error/loading/empty states** — `qatalyst-new-screen` and `xml-ui.instructions.md` stop at wiring;
   nothing requires a screen to handle or test a failure/loading/empty state.
3. **Stuck runs are only caught by the agent's own count** — `qatalyst-developer` stops and asks
   after 3 failed attempts at the same failure, or a build/test command silent for 10 minutes
   (and `qatalyst-ticket-ship` does the same for its build and tests), but that
   relies on the agent noticing. A run that hangs outright (model or tool never returns) can't
   report itself, and no timer or hook exists to do it; the developer's recovery is to stop the
   chat and run `/qatalyst-ticket-start` again. `qatalyst-test-writer` has no cap of its own.
4. **"Resolved" is undefined** for review comments — unclear if a developer override counts.
5. **Ticket reclassified after `qatalyst-ticket-start` runs** — issue type is read once; a later
   feature→bug (or reverse) reclassification isn't re-checked.
6. **Technically-passing-but-wrong-approach implementations** — `qatalyst-code-reviewer` checks
   criteria are
   met, not that the approach matches `tasks.md`'s Approach section's intent.
7. **Flaky test passes** — the gate is "passed locally, once"; no rule addresses intermittent tests.
8. **Branch/feature-folder collisions** — no rule for two tickets proposing the same slug.
9. **Plan-only test categories have no execution gate** — `qatalyst-interop-test-writer`, `qatalyst-ota-test-writer`,
    `qatalyst-performance-test-writer`, and `qatalyst-chaos-test-writer` only guarantee a plan file exists and is
    current; nothing in this workflow checks that a human actually ran it against real hardware
    before the ticket is committed, or records the result anywhere `qatalyst-ticket-ship` can see.
10. **No guard on commands or secrets** — with the hooks gone, nothing mechanical stops an agent
    from running `git push --force`, reading a keystore or the raw logs, or posting a token in a
    Jira or PR comment; only the written rules and Copilot's own approval prompts stand in the way.

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
├── .gitignore                         .logs/, .github/, .repowise/, .vscode/, docs/workflow-design.md, specs/.templates/ ignored
├── specs/
│   └── .templates/
│       └── tasks-template.md          scaffold only — see §10.3 for the -template.md convention
├── .logs/                             created lazily, git-ignored — see §10.2
└── .github/
    ├── workflow-sync.md               written every install.sh run — version, commit, timestamp; never hand-edited
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
    │   └── scripts/logcat_context.py   what the trim and digest leave out: lead-up, other processes, lifecycle, history, versions
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
    │   ├── qatalyst-ask-developer/SKILL.md            cross-cutting
    │   ├── qatalyst-commit-message/SKILL.md           cross-cutting
    │   ├── qatalyst-write-tests/SKILL.md
    │   ├── qatalyst-ticket-start/SKILL.md
    │   └── qatalyst-ticket-ship/SKILL.md              review, token report, commit message, build/tests, local commit
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
    └── token-tracker/
        ├── scripts/token_tracker.py   mark / collect / report — per-ticket token usage
        ├── scripts/token_credits.py   price sheet (.xlsx) + token-usage.html/.json -> AI credits per model and agent; stdlib only
        └── vscode-settings.json       the one VS Code setting tracing needs; copied to .vscode/settings.json if the app repo has none
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
├── raw/                 as captured (.txt/.log, or a .zip) — qatalyst-log-analyser's rules say never read it; the attachment download (a single https `curl -o`) writes here
│   └── extracted/        logcat_extract.py's output — still the full raw log, so the same rule applies
├── trimmed.log           redacted + windowed — what qatalyst-log-analyser actually reads
├── digest.md             error groups with counts and first/last times
├── workflow-report.md    written when every task is ticked: analysis passes (bugs), what changed, who depends on it, risk, and whether Repowise's index was used
└── in-progress.json      only while a task or the commit step runs; still there on resume = the last chat broke midway

.logs/token-tracker/
├── markers.jsonl         one line per `token_tracker.py mark` — ticket ID + time
├── calls.jsonl           every model call copied from Copilot's traces (they expire after 7 days)
└── <ticket-id>/
    ├── token-usage.html  the report as a page; opened by report --open
    └── token-usage.json  ticket, executor, priceUnit, totalCost, start/end time; steps[] per agent with
                          calls[] (fresh/cached/cache-write input, output, cost)
```

### 10.3 Naming conventions: specification compliance

Every path under `.github/` conforms to a documented GitHub Copilot customization path, verified
against the [customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet),
with two exceptions: `.github/workflow-sync.md` and `.github/token-tracker/`, project-specific
conventions this workflow keeps there purely because `.github/` is where the rest of its files
already live. Every path outside
`.github/` — `specs/`, the `-template.md` suffix — is also a project-specific convention introduced
by this workflow; GitHub Copilot has no knowledge of any of these and assigns them no behavior.

| Path / suffix | Classification | Notes |
|---|---|---|
| `.github/copilot-instructions.md` | GitHub Copilot specification | Repository-wide instructions |
| `.github/instructions/*.instructions.md` | GitHub Copilot specification | Path-specific instructions; requires an `applyTo` front-matter field |
| `.github/prompts/*.prompt.md` | GitHub Copilot specification | Slash-command shortcuts |
| `.github/agents/*.md` | Location per specification; `.agent.md` suffix is a project convention | The specification requires only that the file reside in `.github/agents/`; the `.agent.md` suffix is applied by this workflow for readability and is not required by GitHub Copilot |
| `.github/skills/<name>/SKILL.md` | GitHub Copilot specification | Also valid under `.claude/skills/` or `.agents/skills/`; this workflow does not write to either location |
| `.github/workflow-sync.md` | Project-specific convention | Not a GitHub Copilot concept; written fresh by every `install.sh` run, never hand-edited |
| `.github/token-tracker/` | Project-specific convention | Not a GitHub Copilot concept; scripts that read Copilot's local traces. Only the setting it relies on, `github.copilot.chat.otel.dbSpanExporter.enabled`, is Copilot's own |
| `specs/<bug\|feature>/<ticket-id>/` | Project-specific convention | Not a GitHub Copilot concept; the path is computed deterministically (never asked about) and honored by `qatalyst-bug-planner`, `qatalyst-feature-planner`, and `qatalyst-log-analyser` |
| `specs/.templates/*-template.md` | Project-specific convention | The `-template` suffix excludes the scaffold from any glob that scans `specs/**/tasks.md` for live ticket specs, while the `.md` extension preserves Markdown rendering in editors and previews |
| `jira_projects` settings-block field (and its per-entry `key`/`bug_issue_types`) | Project-specific convention | Not a GitHub Copilot concept; read by `qatalyst-ticket-start` at the start of every ticket |

**Implication.** A path classified as GitHub Copilot specification is governed by GitHub's
published behavior and remains valid for as long as that specification does. A path classified as a
project-specific convention carries no external enforcement — it functions only because every
agent and skill that reads or writes it has been written to honor it consistently. Any change to
the `specs/` layout or the `-template.md` convention must therefore be mirrored across all of them.
