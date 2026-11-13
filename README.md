# Agentic AI-SDLC Workflow

This repo holds the Copilot customization for this Android app — agents, skills, path
instructions, hooks, prompts and MCP config, checked in and used as-is. There is no generator
wizard: a change here is a direct edit to the live workflow files, same as any other change. The
only other moving part is [`install.sh`](install.sh)/[`install.ps1`](install.ps1), which copies
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
| **`.github/mcp/`** | Reference MCP server snippet for JetBrains (copy into your own local JetBrains `mcp.json`) |
| **`.mcp.json`** | Portable workspace MCP server config — the one file VS Code Copilot and the Copilot CLI both actually auto-discover |
| **`.github/log-analyser/`** | The log-analysis loop's scripts and `log-signatures.md` |
| **`project-context.md`**, **`architecture.md`** | What this app is and how it's built — filled in once by hand, then edited directly as facts change (never regenerated) |
| **`specs/.templates/`** | Scaffold for `tasks.md` — a ticket's one spec file — copied into a ticket's own `specs/<bug\|feature>/<ticket-id>/` folder |
| **`docs/workflow-design.md`** | Combined technical reference: flowcharts, tables, folder structure, known gaps |
| **`install.sh`**, **`install.ps1`** | Downloads this repo and syncs its workflow files into the app repo (see §2) |
| **`VERSION`**, **`CHANGELOG.md`** | This workflow's own version and change history — bumped and entered for every change that lands here; `install.sh`/`install.ps1` read both at sync time (see §2) |

## 2. One-time setup

Run this from inside the Android app repo you want the workflow in:

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash
```

```powershell
# Windows
irm https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.ps1 | iex
```

This downloads this repo and copies `.github/` (agents, skills, instructions, hooks, prompts,
the JetBrains MCP reference snippet, log-analyser scripts), `.mcp.json` if the app repo doesn't
already have one, `specs/.templates/`, and `docs/workflow-design.md` +
`docs/field-sources.md` into the app repo. Run it again any time this repo changes, to pick up the
update — it always overwrites those files (they're maintained here, not hand-edited per app repo),
but never overwrites `copilot-instructions.md`, `.mcp.json`, `project-context.md`, `architecture.md`,
`hooks/sensitive-paths.txt` or `log-analyser/log-signatures.md` if they already exist, since those
hold the app repo's own project data. Everything it touches lands in a normal git working tree, so
`git status`/`git diff` shows exactly what changed and it's trivially reversible.

Every run also writes `.github/workflow-sync.md` into the app repo, recording which version and
commit of this workflow it just synced from, and when. Check that file to see what an app repo is
currently running, and this repo's [`CHANGELOG.md`](CHANGELOG.md) to see what changed since.

### 2a. Manual install (no shell access, e.g. this repo downloaded as a `.zip`)

If you can't run `install.sh`/`install.ps1` — a locked-down machine, or you only have this repo as
an extracted `.zip` — copy files by hand instead, but **only these paths**, not the whole
extracted folder:

- `.github/agents/`, `.github/instructions/`, `.github/skills/`, `.github/prompts/`,
  `.github/log-analyser/scripts/` (just the scripts, not `log-signatures.md`), `.github/mcp/`,
  `.github/hooks/scripts/` — for each of these, **delete the app repo's existing folder first,
  then copy the new one in**; don't paste on top of what's there. `install.sh` does this same
  delete-then-copy itself (`sync_dir`'s `rm -rf` before its `cp`), specifically so a file renamed
  or removed in this repo disappears from the app repo too. Pasting on top instead leaves the old
  file sitting next to the new one — e.g. an old `ticket-start.prompt.md` next to the current
  `qatalyst-ticket-start.prompt.md` — which is a real risk given the renames this workflow went
  through. `.github/hooks/guards.json` and `.github/hooks/hook-protocol.md` are single files —
  just overwrite them directly, no folder to delete.
- `specs/.templates/`, `docs/workflow-design.md`, `docs/field-sources.md` — same: delete and
  replace the folder, overwrite the two single files directly.
- `.github/copilot-instructions.md`, `.github/hooks/sensitive-paths.txt`,
  `.github/log-analyser/log-signatures.md`, `.mcp.json`, `project-context.md`, `architecture.md` —
  copy these **only if the app repo doesn't already have them**. If it does, leave them alone;
  they hold that app's own settings and data, not this repo's.
- Add `.logs/` to the app repo's `.gitignore` if it's not already there.
- If your file manager ever offers to "keep both" on a naming conflict instead of replacing,
  decline it — that's how literal duplicate files (`name (1).md`) end up committed by accident.

**Never copy** `README.md`, `install.sh`, `install.ps1`, `VERSION`, `CHANGELOG.md`, or `tests/` —
those describe and maintain this source repo, not the app repo, and have no place there. This is
exactly what `install.sh`/`install.ps1` automate; use one of them instead of this section whenever
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
   `mcp.json` location (not this repo), so copy `.github/mcp/jetbrains-mcp.example.json` into it
   instead. Bitbucket PR tools may need a separate local API-token configuration. Never commit a
   filled-in token or credential.

Optional integrations (Atlassian Rovo MCP, Figma MCP, Repowise) enhance the agents but aren't
required to start using the workflow.

## 3. Daily operational workflow

### Starting a ticket

**Command:** `/qatalyst-ticket-start <ticket ID>`

**Or, without typing a command:** pick `qatalyst-ticket` from Copilot Chat's custom-agent picker
instead — it's the one agent in this workflow marked `user-invocable: true`, so it's the only one
that shows up there. Selecting it starts the same `qatalyst-ticket-start` flow; it just asks for
the ticket ID conversationally if you don't give one with your first message. Every other agent in
this workflow is `user-invocable: false` — hidden from the picker, only ever reached by one agent
handing off to another, never by picking it yourself.

1. Reads the ticket's Jira issue type against `copilot-instructions.md`'s configured
   `bug_issue_types`; routes to the log-analysis loop automatically for a bug, no separate step.
2. Hands off to `qatalyst-bug-planner` (for a bug) or `qatalyst-feature-planner` (otherwise), which
   reads the ticket, its Confluence pages and Figma links, writes to the deterministic
   `specs/<bug|feature>/<ticket ID>/tasks.md` path, and produces one `tasks.md` — a single approval,
   not three.
3. Creates the feature branch and asks before moving the ticket to In Progress.

### Implementation & testing

Developers work `tasks.md` one task at a time. `qatalyst-developer` implements; `qatalyst-test-writer`
covers it with
tests. Project skills (`/qatalyst-new-screen`, `/qatalyst-new-ble-command`, `/qatalyst-new-api-call`, `/qatalyst-room-migration`) handle
the per-layer detail; `/qatalyst-new-feature` orchestrates all of them for a task that spans the stack.

### Shipping

**Command:** `/qatalyst-ticket-ship`

1. Confirms every task is ticked.
2. Runs `qatalyst-code-reviewer` (and `qatalyst-security-reviewer`/`qatalyst-error-handling-reviewer`
   for flagged diffs) against
   the spec.
3. Builds and tests locally.
4. Asks once, then commits, pushes, opens the Bitbucket PR, waits on Pipelines where it's on, and
   moves the ticket to In Review.

## 4. Maintenance

This is just a repo now — no regeneration step, no "blueprint vs. generated copy" distinction.
Change an agent, skill, instruction, hook or prompt by editing its file directly under `.github/`
and committing, same as any other code change in this repo.

**Risk management:** known architectural constraints — test/spec gaming vectors, no automated retry
cap, flaky-test passes, and others — are tracked in [`docs/workflow-design.md`](docs/workflow-design.md)
§10, for ongoing mitigation.
