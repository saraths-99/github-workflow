# Agentic AI-SDLC Workflow

This repo holds the Copilot customization for this Android app — agents, skills, path
instructions, prompts and MCP config, checked in and used as-is. There is no generator
wizard: a change here is a direct edit to the live workflow files, same as any other change. The
only other moving part is [`install.sh`](install.sh), which copies
these files into the actual app repo (see §2) and re-syncs them after a later update here.

For the full design reference — flowcharts, the agent and skill tables, risk log, and exactly
where every file lives — see [`docs/workflow-design.md`](docs/workflow-design.md).

## 1. What's here

| Directory / file | Holds |
| ----- | ----- |
| **`.github/copilot-instructions.md`** | Settings block (Jira projects, base branch), module map, key rules, links to the context docs |
| **`.github/instructions/`** | Path-scoped instructions: Kotlin, XML UI, Koin DI, BLE (Halo + GDO), data layer, testing, Gradle |
| **`.github/agents/`** | The 19 agents: the entry point `qatalyst-ticket` (the only one you can pick), planning/build (`qatalyst-log-ticket-intake`, `qatalyst-log-analyser`, `qatalyst-bug-planner`, `qatalyst-feature-planner`, `qatalyst-developer`), review (`qatalyst-code-reviewer`, `qatalyst-security-reviewer`, `qatalyst-error-handling-reviewer`), and testing — `qatalyst-test-writer` routing to 9 specialized writers (`qatalyst-unit-test-writer`, `qatalyst-ble-protocol-test-writer`, `qatalyst-androidtest-writer`, `qatalyst-compatibility-test-writer`, `qatalyst-security-test-writer`, `qatalyst-interop-test-writer`, `qatalyst-ota-test-writer`, `qatalyst-performance-test-writer`, `qatalyst-chaos-test-writer`). See docs/workflow-design.md §4 |
| **`.github/skills/`** | Orchestration (`qatalyst-ticket-start`, `qatalyst-ticket-ship`, `qatalyst-write-tests`), implementation (`qatalyst-new-feature`, `qatalyst-new-screen`, `qatalyst-new-ble-command`, `qatalyst-new-api-call`, `qatalyst-room-migration`), and shared helpers the agents call (`qatalyst-plan-ticket`, `qatalyst-jira-ticket-intake`, `qatalyst-spec-folder-resolution`, `qatalyst-repowise-lookup`, `qatalyst-ask-developer`, `qatalyst-koin-wiring`) |
| **`.github/prompts/`** | `*.prompt.md` files behind each slash command: `/qatalyst-ticket-start`, `/qatalyst-ticket-ship`, `/log-analyser`, `/qatalyst-write-tests`, and the `/qatalyst-new-*` and `/qatalyst-room-migration` skills' commands |
| **`.github/mcp/`** | Reference MCP server snippet for JetBrains (copy into your own local JetBrains `mcp.json`); stays in this repo, not installed |
| **`.mcp.json`** | Portable workspace MCP server config (Atlassian and Repowise) — the one file VS Code Copilot and the Copilot CLI both actually auto-discover. Its Repowise entry has two placeholders to fill in per machine |
| **`.github/workflow-guide.md`** | The developer's guide to using the workflow day to day: Repowise, MCP servers, per-IDE differences, the ticket flow (read it in the app repo) |
| **`.github/log-analyser/`** | The log-analysis loop's scripts |
| **`.github/token-tracker/`** | Per-ticket token usage: `token_tracker.py` and the VS Code setting it needs (VS Code only) (see the guide's "Token usage per ticket") |
| **`project-context.md`**, **`architecture.md`** | What this app is and how it's built — filled in once by hand, then edited directly as facts change (never regenerated) |
| **`specs/.templates/`** | Scaffold for `tasks.md` — a ticket's one spec file — copied into a ticket's own `specs/<bug\|feature>/<ticket-id>/` folder |
| **`docs/workflow-design.md`** | Combined technical reference: flowcharts, tables, folder structure, known gaps |
| **`install.sh`**, **`models.json`**, **`set-models.py`** | Downloads this repo and syncs its workflow files into the app repo, setting every agent to the chosen provider's models (see §2) |
| **`VERSION`**, **`CHANGELOG.md`** | This workflow's own version and change history — bumped and entered for every change that lands here; `install.sh` reads both at sync time (see §2) |

## 2. One-time setup

Run this from inside the Android app repo you want the workflow in (macOS or Linux; the workflow
doesn't support Windows):

```bash
curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash
```

The first install asks which models the agents should run on, **Claude** or **GPT**, and sets every
agent and prompt to that provider's models (the lists are in `models.json`). To skip the question or
change the choice later, run it again with `--provider claude` or `--provider gpt`:

```bash
curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash -s -- --provider gpt
```

With no terminal to ask on, it uses Claude. Later runs reuse the choice recorded in
`.github/workflow-sync.md`.

This downloads this repo and copies `.github/` (agents, skills, instructions, prompts,
log-analyser scripts, token tracker), `.mcp.json` if the app repo doesn't already have one,
`specs/.templates/`, and `docs/workflow-design.md` into the app repo. Reference material only a
person reads once — the JetBrains MCP snippet, `docs/field-sources.md` — stays here and isn't installed; an older install's copies of
them are removed, along with the guard hooks it used to install (see the changelog). Run it
again any time this repo changes, to pick up the update — it always overwrites those files (they're maintained here, not hand-edited per app repo),
but never overwrites `copilot-instructions.md`, `.mcp.json`, `project-context.md`, `architecture.md`
if they already exist, since those
hold the app repo's own project data. It also adds `.logs/`, `.github/`, `.repowise/`, `.vscode/`, `docs/workflow-design.md` and
`specs/.templates/` to the app repo's `.gitignore`, so the workflow files, the design doc, the task
template, the per-ticket logs, Repowise's index and the VS Code settings stay out of the app's
commits. A ticket's own `specs/<bug|feature>/<ticket ID>/` folder is not ignored. Files already tracked in the app repo's `.github/` or `.vscode/` stay tracked, and git still
shows changes to them. A new file there needs `git add -f`.

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
  `.github/log-analyser/scripts/`, `.github/token-tracker/` — for each of these, **delete the app repo's existing folder first,
  then copy the new one in**; don't paste on top of what's there. `install.sh` does this same
  delete-then-copy itself (`sync_dir`'s `rm -rf` before its `cp`), specifically so a file renamed
  or removed in this repo disappears from the app repo too. Pasting on top instead leaves the old
  file sitting next to the new one — e.g. an old `ticket-start.prompt.md` next to the current
  `qatalyst-ticket-start.prompt.md` — which is a real risk given the renames this workflow went
  through.
- `specs/.templates/`, `docs/workflow-design.md`, `.github/workflow-guide.md` — same: delete and
  replace the folder, overwrite the single files directly.
- `.github/copilot-instructions.md`, `.mcp.json`,
  `project-context.md`, `architecture.md` —
  copy these **only if the app repo doesn't already have them**. If it does, leave them alone;
  they hold that app's own settings and data, not this repo's.
- Add `.logs/`, `.github/`, `.repowise/`, `.vscode/`, `docs/workflow-design.md` and `specs/.templates/` to the app repo's `.gitignore` if they're not already there.
- The copied agents and prompts run on Claude's models. For GPT, run
  `python3 set-models.py gpt <path to the app repo>` from this repo after copying (it needs Python 3).
- Copy `.github/token-tracker/vscode-settings.json` to `.vscode/settings.json` only if the app repo
  has no such file; otherwise add its one line to the existing file. The setting doesn't appear in
  VS Code's Settings screen, so searching for it finds nothing: it goes in a settings JSON file. Then
  run **Developer: Reload Window**, send one Copilot chat message, and check that `agent-traces.db`
  now exists (see the guide's "Token usage per ticket"). A ticket worked before then reports 0 calls.
- If your file manager ever offers to "keep both" on a naming conflict instead of replacing,
  decline it — that's how literal duplicate files (`name (1).md`) end up committed by accident.

**Never copy** `README.md`, `install.sh`, `models.json`, `set-models.py`, `VERSION`, `CHANGELOG.md`,
`tests/`, `.github/mcp/` or `docs/field-sources.md` — those describe and
maintain this source repo, or are reference material read from here, and have no place in the app
repo. This is
exactly what `install.sh` automates; use it instead of this section whenever
you can — it's easy to copy a stray file by hand that `sync_dir`/`keep_if_present` would have
known to skip.

Then, in the app repo, open it in an IDE with GitHub Copilot (Android Studio or VS Code; the
[workflow guide](.github/workflow-guide.md#your-ide-at-a-glance) shows what differs between them and the Copilot CLI). Three things
still need filling in by hand, since no tool can read them off the code or guess them:

1. **`.github/copilot-instructions.md`'s settings block** — your real `base_branch` (the Jira project key is
   added from your first ticket, with `Bug` as its bug type, so change `bug_issue_types` if yours is named
   differently). Also fill in its module map and key-rules bullets.
2. **`project-context.md` / `architecture.md`** — draft these once from the real code (see
   [`docs/field-sources.md`](docs/field-sources.md) for what counts as solid evidence per field),
   get a developer to confirm the draft, then never regenerate them — edit by hand as facts change.
3. **MCP servers** — in `.mcp.json`, replace the two Repowise placeholders (the path to the `repowise`
   program and the folder that holds all your repos), then sign in to Atlassian once per machine; see
   the [guide](.github/workflow-guide.md#mcp-servers).

## 3. Day-to-day use

Everything a developer needs once the workflow is installed lives in
[`.github/workflow-guide.md`](.github/workflow-guide.md), which `install.sh` copies into the app
repo: setting up Repowise and the MCP servers, what differs between VS Code, Android Studio and the
Copilot CLI, the daily ticket flow, and token usage. This README covers what's in this repo and how
to install and update it.

## 4. Maintenance

This is just a repo now — no regeneration step, no "blueprint vs. generated copy" distinction.
Change an agent, skill, instruction or prompt by editing its file directly under `.github/`
and committing, same as any other code change in this repo.

**Risk management:** known architectural constraints — test/spec gaming vectors, no automated retry
cap, flaky-test passes, and others — are tracked in [`docs/workflow-design.md`](docs/workflow-design.md)
§9, for ongoing mitigation.
