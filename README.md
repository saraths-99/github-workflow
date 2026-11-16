# Agentic AI-SDLC Workflow

This repo holds the Copilot customization for this Android app — agents, skills, path
instructions, hooks, prompts and MCP config, checked in and used as-is. There is no generator
wizard: a change here is a direct edit to the live workflow files, same as any other change. The
only other moving part is [`install.sh`](install.sh), which copies
these files into the actual app repo (see §2) and re-syncs them after a later update here.

For the full design reference — flowcharts, the agent/skill/hook tables, risk log, and exactly
where every file lives — see [`docs/workflow-design.md`](docs/workflow-design.md).

## 1. What's here

| Directory / file | Holds |
| ----- | ----- |
| **`.github/copilot-instructions.md`** | Settings block (Jira projects, base branch), module map, key rules, links to the context docs |
| **`.github/instructions/`** | Path-scoped instructions: Kotlin, XML UI, Koin DI, BLE (Halo + GDO), data layer, testing, Gradle |
| **`.github/agents/`** | The 17 agents: planning/build (`qatalyst-log-analyser`, `qatalyst-bug-planner`, `qatalyst-feature-planner`, `qatalyst-developer`), review (`qatalyst-code-reviewer`, `qatalyst-security-reviewer`, `qatalyst-error-handling-reviewer`), and testing — `qatalyst-test-writer` routing to 9 specialized writers (`qatalyst-unit-test-writer`, `qatalyst-ble-protocol-test-writer`, `qatalyst-androidtest-writer`, `qatalyst-compatibility-test-writer`, `qatalyst-security-test-writer`, `qatalyst-interop-test-writer`, `qatalyst-ota-test-writer`, `qatalyst-performance-test-writer`, `qatalyst-chaos-test-writer`) — the 9 specialized writers and the `qatalyst-` prefix migration are tracked separately; see docs/workflow-design.md §4 |
| **`.github/skills/`** | Orchestration (`qatalyst-ticket-start`, `qatalyst-ticket-ship`, `qatalyst-write-tests`) and implementation skills (`qatalyst-new-feature`, `qatalyst-new-screen`, `qatalyst-new-ble-command`, `qatalyst-new-api-call`, `qatalyst-room-migration`) |
| **`.github/prompts/`** | `*.prompt.md` files behind each slash command |
| **`.github/hooks/`** | `guards.json` + the guard scripts (format, force-push block, secret protection, context-doc guard) |
| **`.github/mcp/`** | Reference MCP server snippet for JetBrains (copy into your own local JetBrains `mcp.json`); stays in this repo, not installed |
| **`.mcp.json`** | Portable workspace MCP server config — the one file VS Code Copilot and the Copilot CLI both actually auto-discover |
| **`.github/log-analyser/`** | The log-analysis loop's scripts |
| **`.github/token-tracker/`** | Per-ticket token usage: `token_tracker.py`, the Copilot CLI launchers, and the VS Code setting it needs (see §3, "Token usage per ticket") |
| **`project-context.md`**, **`architecture.md`** | What this app is and how it's built — filled in once by hand, then edited directly as facts change (never regenerated) |
| **`specs/.templates/`** | Scaffold for `tasks.md` — a ticket's one spec file — copied into a ticket's own `specs/<bug\|feature>/<ticket-id>/` folder |
| **`docs/workflow-design.md`** | Combined technical reference: flowcharts, tables, folder structure, known gaps |
| **`install.sh`** | Downloads this repo and syncs its workflow files into the app repo (see §2) |
| **`VERSION`**, **`CHANGELOG.md`** | This workflow's own version and change history — bumped and entered for every change that lands here; `install.sh` reads both at sync time (see §2) |

## 2. One-time setup

Run this from inside the Android app repo you want the workflow in (macOS or Linux; the workflow
doesn't support Windows):

```bash
curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash
```

This downloads this repo and copies `.github/` (agents, skills, instructions, hooks, prompts,
log-analyser scripts, token tracker), `.mcp.json` if the app repo doesn't already have one,
`specs/.templates/`, and `docs/workflow-design.md` into the app repo. Reference material only a
person reads once — the JetBrains MCP snippet, `docs/field-sources.md`,
`.github/hooks/hook-protocol.md` — stays here and isn't installed; an older install's copies of
them are removed. Run it again any time this repo changes, to pick up the
update — it always overwrites those files (they're maintained here, not hand-edited per app repo),
but never overwrites `copilot-instructions.md`, `.mcp.json`, `project-context.md`, `architecture.md`,
or `hooks/sensitive-paths.txt` if they already exist, since those
hold the app repo's own project data. Everything it touches lands in a normal git working tree, so
`git status`/`git diff` shows exactly what changed and it's trivially reversible.

If the app repo has no `.vscode/settings.json`, the install also creates one holding the single
Copilot setting token tracking needs. If it already has one, the install leaves it alone and prints
the line to add yourself.

Every run also writes `.github/workflow-sync.md` into the app repo, recording which version and
commit of this workflow it just synced from, and when. Check that file to see what an app repo is
currently running, and this repo's [`CHANGELOG.md`](CHANGELOG.md) to see what changed since.

### 2a. Manual install (no shell access, e.g. this repo downloaded as a `.zip`)

If you can't run `install.sh` — a locked-down machine, or you only have this repo as
an extracted `.zip` — copy files by hand instead, but **only these paths**, not the whole
extracted folder:

- `.github/agents/`, `.github/instructions/`, `.github/skills/`, `.github/prompts/`,
  `.github/log-analyser/scripts/`, `.github/token-tracker/`,
  `.github/hooks/scripts/` — for each of these, **delete the app repo's existing folder first,
  then copy the new one in**; don't paste on top of what's there. `install.sh` does this same
  delete-then-copy itself (`sync_dir`'s `rm -rf` before its `cp`), specifically so a file renamed
  or removed in this repo disappears from the app repo too. Pasting on top instead leaves the old
  file sitting next to the new one — e.g. an old `ticket-start.prompt.md` next to the current
  `qatalyst-ticket-start.prompt.md` — which is a real risk given the renames this workflow went
  through. `.github/hooks/guards.json` is a single file — just overwrite it directly, no folder
  to delete.
- `specs/.templates/`, `docs/workflow-design.md` — same: delete and replace the folder,
  overwrite the single file directly.
- `.github/copilot-instructions.md`, `.github/hooks/sensitive-paths.txt`, `.mcp.json`,
  `project-context.md`, `architecture.md` —
  copy these **only if the app repo doesn't already have them**. If it does, leave them alone;
  they hold that app's own settings and data, not this repo's.
- Add `.logs/` to the app repo's `.gitignore` if it's not already there.
- Copy `.github/token-tracker/vscode-settings.json` to `.vscode/settings.json` only if the app repo
  has no such file; otherwise add its one line to the existing file.
- If your file manager ever offers to "keep both" on a naming conflict instead of replacing,
  decline it — that's how literal duplicate files (`name (1).md`) end up committed by accident.

**Never copy** `README.md`, `install.sh`, `VERSION`, `CHANGELOG.md`, `tests/`,
`.github/mcp/`, `.github/hooks/hook-protocol.md` or `docs/field-sources.md` — those describe and
maintain this source repo, or are reference material read from here, and have no place in the app
repo. This is
exactly what `install.sh` automates; use it instead of this section whenever
you can — it's easy to copy a stray file by hand that `sync_dir`/`keep_if_present` would have
known to skip.

Then, in the app repo, open it in an IDE with GitHub Copilot (JetBrains or VS Code). Two things
still need filling in by hand, since no tool can read them off the code or guess them:

1. **`.github/copilot-instructions.md`'s settings block** — your real Jira project key(s),
   `bug_issue_types`, and `base_branch`. Also fill in its module map and key-rules bullets.
2. **`project-context.md` / `architecture.md`** — draft these once from the real code (see
   [`docs/field-sources.md`](docs/field-sources.md) for what counts as solid evidence per field),
   get a developer to confirm the draft, then never regenerate them — edit by hand as facts change.
3. **MCP setup** — both VS Code Copilot and the Copilot CLI read the workspace-root `.mcp.json`
   directly; enable the workspace MCP config option if your VS Code version requires it, then sign
   in to the servers as prompted. If your app repo already had `.mcp.json`, merge the
   `atlassian-rovo`, `figma`, and `repowise` servers into it. JetBrains has its own separate
   `mcp.json` location (not the app repo), so copy this repo's
   [`.github/mcp/jetbrains-mcp.example.json`](.github/mcp/jetbrains-mcp.example.json) into it
   instead. Bitbucket PR tools may need a separate local API-token configuration. Never commit a
   filled-in token or credential. The `repowise` server only works once Repowise is installed and
   has indexed the app repo — see §2b.

Optional integrations (Atlassian Rovo MCP, Figma MCP, Repowise) enhance the agents but aren't
required to start using the workflow.

### 2b. Repowise (optional)

Repowise gives the planners, developer, test writers and reviewers the app's call graph, change
risk and hotspots (through `qatalyst-repowise-lookup`). Without it they fall back to plain file
search, so nothing breaks — they just see less. Set it up once per developer machine:

1. **Install it.** Needs Python 3.11 or newer.

   ```bash
   pipx install repowise
   ```

2. **Index the app repo**, from its root:

   ```bash
   repowise init --yes --no-prose --no-editor-setup
   ```

   - `--no-prose` builds the index from the code alone: no model, no API key, and none of the
     app's code is sent anywhere.
   - `--no-editor-setup` keeps the run to `.repowise/` and nothing else. **Never leave it off.**
     Without it, `init` writes `CLAUDE.md`, `AGENTS.md` and `.vscode/mcp.json` into the app repo,
     re-points machine-wide editor configs at this repo, and wires up every editor it finds.
     None of that belongs in this workflow: `.mcp.json` already starts Repowise for Copilot, a
     second entry in `.vscode/mcp.json` starts it twice, and `AGENTS.md` would compete with
     `copilot-instructions.md`.

3. **Keep the index current** after every commit:

   ```bash
   repowise hook install
   ```

   This adds a git post-commit hook that runs `repowise update`. If you'd rather not, run
   `repowise update` yourself before starting a ticket.

4. **Keep `.repowise/` out of git** — it's a per-machine index. Add `.repowise/` to the app repo's
   `.gitignore` if it isn't there.

Check it with `repowise status`. Repowise sends anonymous usage telemetry by default; turn it off
with `repowise telemetry disable` if your project needs that. To remove it from a repo, run
`repowise uninstall --dry-run` to see what it wrote, then `repowise uninstall --all`.

## 3. Daily operational workflow

### Starting a ticket

**Command:** `/qatalyst-ticket-start <ticket ID>`

**Or, without typing a command:** pick `qatalyst-ticket` from Copilot Chat's custom-agent picker
instead — it's the one agent in this workflow marked `user-invocable: true`, so it's the only one
that shows up there. Selecting it starts the same `qatalyst-ticket-start` flow; if you don't give a
ticket ID with your first message, it offers your open Jira tickets to pick from. Every other agent in
this workflow is `user-invocable: false` — hidden from the picker, only ever reached by one agent
handing off to another, never by picking it yourself.

1. Reads the ticket's Jira issue type against `copilot-instructions.md`'s configured
   `bug_issue_types`; routes to the log-analysis loop automatically for a bug, no separate step.
2. Hands off to `qatalyst-bug-planner` (for a bug) or `qatalyst-feature-planner` (otherwise), which
   reads the ticket, its Confluence pages and Figma links, writes to the deterministic
   `specs/<bug|feature>/<ticket ID>/tasks.md` path, and produces one `tasks.md` — a single approval,
   not three.
3. Creates the feature branch and asks before moving the ticket to In Progress.
4. Runs `qatalyst-developer` through every task, then asks whether to ship now; picking "Ship it
   now" runs the shipping steps below in the same chat.

**Picking up where it stopped.** If the chat breaks, or you stop at a question, run
`/qatalyst-ticket-start <ticket ID>` again (in a new chat is fine). It works out where the ticket
is from `tasks.md` and the feature branch: an unapproved draft goes back to the approval question,
a half-done ticket continues from the first unticked task, and a finished one goes to the ship
question. Nothing is re-planned. If the last chat broke in the middle of a task (or of shipping),
it tells you so — which task, when it started, how many files are changed — and asks whether to
continue that task keeping its changes, restart it with the changes stashed, or stop.

**One flow, no typing.** From the command (or the picker) to the PRs, the ticket runs as one flow.
Wherever it stops for you, it asks a question with options to click — approve the plan, skip log
analysis for a UI-only bug, ship now — using VS Code's `askQuestions` tool, `ask_questions` in
Android Studio, or `ask_user` in the Copilot CLI; the only answer you ever type is what to change when you ask for changes to
`tasks.md`. Approving a terminal command (Allow / Allow all) is Copilot's own prompt. The
`qatalyst-ask-developer` skill holds every question and its options.

**In Android Studio:** turn on Agent Skills first (Settings › GitHub Copilot › Chat › Agent; it's a
preview feature) — the ticket flow, planning and the questions are all skills, and without them the
agents run without their instructions. Android Studio's Copilot chat asks its questions with its
own `ask_questions` tool. Its agent picker hides agents by `x-github-copilot-invoke-policy` rather
than `user-invocable`, so every agent here sets both — only `qatalyst-ticket` shows in either IDE.

### Implementation & testing

Developers work `tasks.md` one task at a time. `qatalyst-developer` implements; `qatalyst-test-writer`
covers it with
tests. Project skills (`/qatalyst-new-screen`, `/qatalyst-new-ble-command`, `/qatalyst-new-api-call`, `/qatalyst-room-migration`) handle
the per-layer detail; `/qatalyst-new-feature` orchestrates all of them for a task that spans the stack.
Once the last task is ticked, `qatalyst-developer` shows the ticket's token usage (see below), and
the flow asks whether to ship now.

### Shipping

Runs as the last step of `/qatalyst-ticket-start` when you pick "Ship it now". If you picked
"Stop here, I'll ship later", run it on its own with **`/qatalyst-ticket-ship`**.

1. Confirms every task is ticked.
2. Runs `qatalyst-code-reviewer` (and `qatalyst-security-reviewer`/`qatalyst-error-handling-reviewer`
   for flagged diffs) against
   the spec.
3. Builds and tests locally.
4. Asks once (push and open the PRs, or cancel), then commits, pushes, opens the Bitbucket PR,
   waits on Pipelines where it's on, and moves the ticket to In Review.

### Token usage per ticket

The workflow can report how many tokens a ticket used, split by agent and sub-agent and by model.
It reads only what Copilot records on your own machine; nothing is uploaded, and your prompts and
code are never recorded. Requires Python 3.9 or newer.

**Turning it on, once per machine:**

- **VS Code:** the setting `"github.copilot.chat.otel.dbSpanExporter.enabled": true`. The install
  adds it to `.vscode/settings.json` for you if that file didn't exist; otherwise add it yourself,
  in that file or your user settings. Tracking also stops if VS Code's own `telemetry.telemetryLevel`
  is `off`.
- **Android Studio:** its Copilot chat panel can't record token usage yet (the plugin has no trace
  export). Use the Copilot CLI in Android Studio's terminal instead, started through the launcher so
  tracking is on:

  ```bash
  .github/token-tracker/copilot-tracked.sh ABC-123
  ```

**Seeing a ticket's usage:** `qatalyst-developer` shows it once every task in `tasks.md` is ticked
and opens the HTML report in your browser. To see it at any other time (mid-ticket, or again after
shipping to include the review and ship steps), run:

```bash
python3 .github/token-tracker/scripts/token_tracker.py report ABC-123 --open
```

(Leave out `--open` to skip the browser.) It prints the
summary and writes two files to `.logs/token-tracker/ABC-123/`:

- `token-usage.html`: the report as a page: totals, a bar per agent and per model, and every model
  call. Self-contained (no scripts, nothing fetched from the internet), so it opens offline. Over
  SSH or anywhere else without a local display, `--open` prints the file's path instead.
- `token-usage.json`: one row per model call under `calls` (`ticketId`, `agentName`, `model`,
  `inputTokens`, `outputTokens`, `timestamp`), plus `totals` and a `byAgent` breakdown (calls,
  input, output and total tokens per agent, largest first), for feeding into other tools.

**How a chat gets counted for a ticket:** `/qatalyst-ticket-start` and the CLI launcher record the
ticket ID when they start, and any chat that ran on the ticket's feature branch counts too. A chat
that did neither (for example, planning started from the `qatalyst-ticket` picker that you abandoned
before a branch was created) isn't counted; run
`python3 .github/token-tracker/scripts/token_tracker.py mark ABC-123` at the start of such a chat to
include it. Skills and hooks don't appear as separate rows: they make no model calls of their own.
Copilot deletes its trace data after 7 days, so run `report` (or `collect`) at least weekly on a
long-running ticket; everything it has copied stays in `.logs/token-tracker/`.

## 4. Maintenance

This is just a repo now — no regeneration step, no "blueprint vs. generated copy" distinction.
Change an agent, skill, instruction, hook or prompt by editing its file directly under `.github/`
and committing, same as any other code change in this repo.

**Risk management:** known architectural constraints — test/spec gaming vectors, no automated retry
cap, flaky-test passes, and others — are tracked in [`docs/workflow-design.md`](docs/workflow-design.md)
§10, for ongoing mitigation.
