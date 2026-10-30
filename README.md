# ASSA ABLOY Agentic AI-SDLC Workflow: System & Deployment Overview

This briefing details the **ASSA ABLOY Agentic AI-SDLC Workflow Builder Repository**. Designed as a GitHub Copilot customization system for the smart-lock Android application, this repository serves as a setup engine rather than a standalone product application.

It contains a setup wizard and a suite of `setup-*` skills that, when executed once inside an application repository, generate customized Copilot instructions, agents, skills, prompts, hooks, and Model Context Protocol (MCP) configurations. Following this initialization, development teams rely entirely on a localized set of slash commands (`/ticket-start`, `/ticket-ship`, `/log-analyser`, etc.) to drive specification-driven development, without requiring further interaction with this builder repository.

For comprehensive architectural design—including algorithms, flowcharts, integration tables, risk logs, and the precise folder structure of both this builder repo and a generated app repo—refer to [`docs/workflow-design.md`](docs/workflow-design.md).

## 1. Repository Architecture (Pre-Deployment)

The builder repository is structured to separate documentation, static checks, and the core generation skills.

| Directory / File | Description |
| ----- | ----- |
| **`.github/copilot-instructions.md`** | Operational rules strictly for this builder repository. |
| **`.github/skills/setup-*/`** | The 8 core builder skills. Each is responsible for generating a specific slice of the target application repository. |
| **`.github/prompts/setup-workflow.prompt.md`** | The orchestrator shortcut command, designed to be copied into the target repository. |
| **`docs/`** | Contains `workflow-design.md`, the combined technical reference (design + folder structure). |
| **`tests/static_checks.py`** | Validation script to verify structural integrity against repository blueprints. |
| **`bootstrap.sh` / `.ps1`** | The initial deployment scripts used to transfer setup skills into the target application repository. |

Each `setup-*` skill folder operates on a standard schema:

* `SKILL.md`: Generation methodology and output specifications.

* `references/`: Detection rules parsed from the application repository prior to generation.

* `assets/`: Reviewed blueprint files (the source of truth). **Blueprints must be updated here** rather than modifying generated files in the application repository.

## 2. Deployment & Initialization

Installation requires a one-time execution per application repository. The target repository must be opened in an IDE equipped with GitHub Copilot (JetBrains IDEs or VS Code). Optional integrations (Atlassian Rovo MCP, Figma MCP, Repowise) will enhance generated agents if configured, but are not mandatory for deployment.

**Initial Transfer:**
Run this once per app repo, from a shell (not from inside Copilot chat). The first argument is always the path to this builder repo on your machine; the second is the path to the Android app repo you want to set up — replace both with your own local paths:

```bash
# macOS / Linux
<path-to-this-builder-repo>/bootstrap.sh <path-to-your-app-repo>

# Windows
<path-to-this-builder-repo>\bootstrap.ps1 <path-to-your-app-repo>
```

For example, if you've cloned this repo to `~/github-workflow` and your app project is at `~/dev/smartlock-android`:

```bash
~/github-workflow/bootstrap.sh ~/dev/smartlock-android
```

*Note: This copies every `.github/skills/setup-*/` folder and `.github/prompts/setup-workflow.prompt.md` from this repo into the app repo's own `.github/`. It writes nothing under `~/.copilot/`, and it never touches the app repo's `.agents/`, `.claude/`, `.android-studio/` or `AGENTS.md` — those stay whatever they already were.*

**Workflow Generation:**
Within the target application repository, open Copilot chat and execute:

```
/setup-workflow
```

This orchestrates the generation process through a series of developer-approved gates:

1. **State Detection:** Identifies if this is a re-run by checking for the `generated-by: copilot-workflow` marker.

2. **Context Analysis:** Scans architecture, workflow documentation, Gradle modules, and codebase domains.

3. **Drafting:** Generates missing contextual documents (`project-context.md`, `architecture.md`).

4. **Parameter Configuration:** Prompts for Jira project keys, base branches, and specific bug issue types.

5. **Confirmation Brief:** Presents a comprehensive summary of detected parameters for explicit developer approval.

6. **Sequential Generation:** Writes configuration layers (Instructions → Agents → Skills → Hooks → MCP → Ticket Flow).

7. **Handoff:** Provides final manual steps, such as committing files and injecting Atlassian tokens into the MCP configuration, and asks once whether to delete the `setup-*` skills now that generation is done (kept by default — deleting them means a later re-run needs `bootstrap.sh` run again first).

## 3. Post-Deployment Architecture

Following a successful `/setup-workflow` execution, the application repository will be equipped with the following customized structure:

| Component Category | Generated Artifacts |
| ----- | ----- |
| **Core Instructions** | `copilot-instructions.md` (settings and global rules), plus path-scoped instructions (`kotlin`, `xml-ui`, `koin-di`, `testing`, etc.). |
| **AI Agents** | 7 specialized agents: `log-analyser`, `ticket-analyst`, `architect`, `developer`, `test-writer`, `code-reviewer`, `security-reviewer`. |
| **Operational Skills** | Orchestration (`ticket-start`, `ticket-ship`), project skills (`new-feature`, `room-migration`), and bug triage (`log-analyser`). |
| **Commands & Prompts** | `*.prompt.md` files enabling the designated slash commands for daily operations. |
| **Security Hooks** | `guards.json` enforcing operational safety (`format-kotlin`, `block-force-push`, `protect-secrets`, `guard-context-docs`). |
| **Integrations** | `mcp.json` and structural templates for requirements, design, and tasks. |

## 4. Daily Operational Workflow

Once deployed, development is entirely specification-driven using the generated slash commands.

### Initiating Work

**Command:** `/ticket-start <ticket ID>`

1. Evaluates the Jira issue type. If flagged as a bug, automatically routes to `/log-analyser` for root-cause analysis.

2. Reads associated Jira tickets, Confluence requirements, and Figma designs.

3. Orchestrates requirement drafting (`ticket-analyst`) and technical design/task creation (`architect`), requiring developer approval at each stage.

4. Generates feature branches and updates Jira statuses upon final approval.

### Implementation & Testing

Developers execute work based on the generated `tasks.md`. The `developer` agent implements logic sequentially, while the `test-writer` agent builds corresponding test coverage. Project-specific skills (e.g., `/new-screen`, `/new-api-call`) can be invoked as needed.

### Shipping & Review

**Command:** `/ticket-ship`

1. Verifies all tasks are completed.

2. Triggers `code-reviewer` (and `security-reviewer` for sensitive domains) to audit diffs against specifications.

3. Presents a final review of repositories, PR text, and merge sequences.

4. Upon approval: commits, pushes, opens cross-linked Bitbucket PRs, verifies CI pipelines, and updates the Jira ticket to "In Review."

## 5. System Components Overview

### Autonomous Agents

| Agent | Primary Responsibility | Scope Limitations |
| ----- | ----- | ----- |
| **`log-analyser`** | Root-causes bug tickets from raw logs. | Writes solely to `log-analysis.md`. |
| **`ticket-analyst`** | Drafts business and technical requirements. | Writes solely to `requirements.md`. |
| **`architect`** | Formulates system design and task breakdowns. | Writes solely to `design.md` and `tasks.md`. |
| **`developer`** | Implements code based on `tasks.md`. | Restricted to single-task execution via named skills. |
| **`test-writer`** | Generates test coverage for implemented tasks. | Edits test files strictly related to the active task. |
| **`code-reviewer`** | Audits implementation against initial specifications. | Read-only verification. |
| **`security-reviewer`** | Reviews code in predefined sensitive areas. | Read-only; activated only by the code-reviewer. |

### Security & Formatting Hooks

| Hook | Trigger Event | Enforcement Action |
| ----- | ----- | ----- |
| **`format-kotlin`** | `postToolUse` | Automatically formats modified `.kt`/`.kts` files. |
| **`block-force-push`** | `preToolUse` | Blocks `git push --force` or `-f` commands. |
| **`protect-secrets`** | `preToolUse` | Prevents modifications to sensitive paths or injection of token-shaped text. |
| **`guard-context-docs`** | `preToolUse` | Requires explicit approval before system context documents are altered. |

## 6. Maintenance & Extensibility

**Safe Re-execution:** The `/setup-workflow` command is safely idempotent. When re-run, it detects existing configurations (preserving Jira keys and base branches) while re-evaluating the codebase for architectural shifts. It strictly preserves any file missing the `generated-by: copilot-workflow` marker to protect manual developer overrides.

**System Expansion:** Modifications to generated instructions, agents, skills, or hooks must be made in this builder repository's `assets/` blueprints. Contributors should run the provided static checks (`python3 tests/static_checks.py`) and validate via local scratch directory before committing updates to the builder core.

**Risk Management:** Known architectural constraints—including test/spec gaming vectors, lack of automated retry caps, and multi-repository partial failure states—are actively tracked in the primary design documentation for ongoing mitigation.
