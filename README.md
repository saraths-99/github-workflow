# Agentic AI-SDLC Workflow

This repo *is* the Copilot customization for this Android app — agents, skills, path instructions,
hooks, prompts and MCP config, checked in and used as-is. There is no generator: a change here is a
change to the live workflow, in the same place and the same commit as everything else in this repo.

For the full design reference — flowcharts, the agent/skill/hook tables, risk log, and exactly
where every file lives — see [`docs/workflow-design.md`](docs/workflow-design.md).

## 1. What's here

| Directory / file | Holds |
| ----- | ----- |
| **`.github/copilot-instructions.md`** | Settings block (Jira projects, base branch), module map, key rules, links to the context docs |
| **`.github/instructions/`** | Path-scoped instructions: Kotlin, XML UI, Koin DI, BLE (Halo + GDO), data layer, testing, Gradle |
| **`.github/agents/`** | The 7 agents: `log-analyser`, `ticket-analyst`, `architect`, `developer`, `test-writer`, `code-reviewer`, `security-reviewer` |
| **`.github/skills/`** | Orchestration (`ticket-start`, `ticket-ship`) and implementation skills (`new-feature`, `new-screen`, `new-ble-command`, `new-api-call`, `room-migration`, `write-tests`) |
| **`.github/prompts/`** | `*.prompt.md` files behind each slash command |
| **`.github/hooks/`** | `guards.json` + the guard scripts (format, force-push block, secret protection, context-doc guard) |
| **`.github/mcp.json`**, **`.github/mcp/`** | MCP server config (Atlassian Rovo, Figma, Repowise) |
| **`.github/log-analyser/`** | The log-analysis loop's scripts and `log-signatures.md` |
| **`project-context.md`**, **`architecture.md`** | What this app is and how it's built — filled in once by hand, then edited directly as facts change (never regenerated) |
| **`specs/.templates/`** | Scaffolds for `requirements.md` / `design.md` / `tasks.md`, copied into a ticket's own `specs/<feature>/<ticket-id>/` folder |
| **`docs/workflow-design.md`** | Combined technical reference: flowcharts, tables, folder structure, known gaps |

## 2. One-time setup

Nothing to install or copy — open this repo in an IDE with GitHub Copilot (JetBrains or VS Code)
and the agents, skills and prompts are already there. Two things still need filling in by hand,
since no tool can read them off the code or guess them:

1. **`.github/copilot-instructions.md`'s settings block** — your real Jira project key(s),
   `bug_issue_types`, and `base_branch`. Also fill in its module map and key-rules bullets.
2. **`project-context.md` / `architecture.md`** — draft these once from the real code (see
   [`docs/field-sources.md`](docs/field-sources.md) for what counts as solid evidence per field),
   get a developer to confirm the draft, then never regenerate them — edit by hand as facts change.
3. **MCP tokens** — copy `.github/mcp/jetbrains-mcp.example.json` into your own JetBrains
   `mcp.json` (or fill in the CLI's local config for `.github/mcp.json`) with your own Atlassian API
   token. Never commit a filled-in token.

Optional integrations (Atlassian Rovo MCP, Figma MCP, Repowise) enhance the agents but aren't
required to start using the workflow.

## 3. Daily operational workflow

### Starting a ticket

**Command:** `/ticket-start <ticket ID>`

1. Reads the ticket's Jira issue type against `copilot-instructions.md`'s configured
   `bug_issue_types`; routes to the log-analysis loop automatically for a bug, no separate step.
2. Reads the ticket, its Confluence pages, Figma links, and the matching workflow doc.
3. Drives `requirements.md` (`ticket-analyst`) then `design.md` + `tasks.md` (`architect`), each
   approved by the developer.
4. Creates the feature branch and asks before moving the ticket to In Progress.

### Implementation & testing

Developers work `tasks.md` one task at a time. `developer` implements; `test-writer` covers it with
tests. Project skills (`/new-screen`, `/new-ble-command`, `/new-api-call`, `/room-migration`) handle
the per-layer detail; `/new-feature` orchestrates all of them for a task that spans the stack.

### Shipping

**Command:** `/ticket-ship`

1. Confirms every task is ticked.
2. Runs `code-reviewer` (and `security-reviewer` for sensitive-area diffs) against the spec.
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
