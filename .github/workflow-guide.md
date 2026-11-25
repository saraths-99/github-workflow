# Workflow guide

How to use this workflow day to day. It's installed into your app repo by `install.sh`, so it's here
when you need it: setting up Repowise and the MCP servers, what differs between VS Code, Android
Studio and the Copilot CLI, and the daily ticket flow, from starting a ticket to shipping it.

Installing and updating the workflow itself is covered in the
[workflow repo's README](https://github.com/saraths-99/github-workflow/blob/develop/README.md), and the full design reference is in
[`docs/workflow-design.md`](../docs/workflow-design.md). Don't edit this file in the app repo: every
install overwrites it.

## Repowise (optional)

Repowise gives the planners, developer, test writers and reviewers the app's call graph, change
risk and hotspots (through `qatalyst-repowise-lookup`). Without it they fall back to plain file
search, so nothing breaks — they just see less. `/qatalyst-ticket-start` checks it at the start of
every ticket and, if it isn't ready, asks you to set it up, continue without it, or stop. Set it up
once per developer machine:

1. **Install it** with [uv](https://docs.astral.sh/uv/). It needs Python 3.11 or newer; uv fetches one
   if you don't have it. uv puts the `repowise` program in `~/.local/bin` by default, which is the
   path the `.mcp.json` entry uses (`which repowise` shows yours).

   ```bash
   uv tool install repowise
   ```

2. **Index the app repo**, from its root:

   ```bash
   repowise init --yes --no-prose --no-editor-setup
   ```

   - **An app built from several repos** checked out side by side: run it once from the folder that
     holds them all, not inside one repo. Repowise indexes each repo and links them, so a lookup
     sees a change's callers in the other repos. Keep them current with `repowise update --workspace`
     and check with `repowise status --workspace`.
   - `--no-prose` builds the index from the code alone: no model, no API key, and none of the
     app's code is sent anywhere.
   - `--no-editor-setup` keeps the run to `.repowise/` and nothing else. **Never leave it off.**
     Without it, `init` writes `CLAUDE.md`, `AGENTS.md` and `.vscode/mcp.json` into the app repo,
     re-points machine-wide editor configs at this repo, and wires up every editor it finds.
     None of that belongs in this workflow: `.mcp.json` already starts Repowise for Copilot, a
     second entry in `.vscode/mcp.json` starts it twice, and `AGENTS.md` would compete with
     `copilot-instructions.md`.

3. **Keep the index current** after every commit. `/qatalyst-ticket-start` does this for you: once
   Repowise is ready it checks `repowise hook status --workspace` and, in each repo without the
   hook (and without a post-commit hook of its own), runs `repowise hook install <repo>`. To do it
   yourself:

   ```bash
   repowise hook install --workspace
   ```

   This adds a git post-commit hook that runs `repowise update`. It lives in each repo's
   `.git/hooks`, not in the repo's tracked files. If you remove it with `repowise hook uninstall`,
   the next ticket puts it back; keep your own `.git/hooks/post-commit` in a repo to stop that.

4. **Keep `.repowise/` out of git** — it's a per-machine index. Add `.repowise/` to the app repo's
   `.gitignore` if it isn't there.

Check it with `repowise status`. Repowise sends anonymous usage telemetry by default; turn it off
with `repowise telemetry disable` if your project needs that. To remove it from a repo, run
`repowise uninstall --dry-run` to see what it wrote, then `repowise uninstall --all`.

## MCP servers

The agents reach Jira, Confluence, Bitbucket and Repowise through MCP servers. The app repo's
`.mcp.json` lists them:

| Server | Used for | Needed? |
|---|---|---|
| `atlassian-rovo` | Reading the ticket and its comments, Confluence pages, moving the ticket, Bitbucket PRs and Pipelines | **Yes** — `/qatalyst-ticket-start` reads the ticket's issue type from Jira, so the flow can't start without it. Without the Bitbucket tools, ship still pushes and gives you the PR text to paste. |
| `repowise` | Code map, callers, change risk | Optional — needs Repowise installed and the repos indexed first (see [Repowise](#repowise-optional)), and its entry filled in as described below |

Keep the server names as they are: the agents find the tools by them (`atlassian-rovo/*`,
`repowise/*`), so a server added under another name is invisible to them. That includes the
Atlassian entry the IDE's MCP registry offers (named `com.atlassian/atlassian-mcp-server`): it points
to the same URL, but under that name the agents don't see its tools. Use `atlassian-rovo` and remove
the registry entry, so only one Atlassian server is listed.

**Fill in the Repowise entry.** The shipped `.mcp.json` has two placeholders in it:

```json
"repowise": {
  "command": "/Users/<USER_PATH>/.local/bin/repowise",
  "args": ["mcp", "<REPOWISE_PROJECT_PARENT_FOLDER>"]
}
```

- `command` is the full path to the `repowise` program (`which repowise` prints it). A full path is
  used because the IDE doesn't always see your shell's `PATH`.
- The second argument is the folder that holds all your repos side by side, the one you ran
  `repowise init` in, so Repowise serves the index for every repo and not just the app repo.
- Both are specific to your machine, so edit your own copy and don't commit it. Install never
  overwrites an existing `.mcp.json`, so your edit survives later installs.
- Until you edit them the `repowise` server fails to start; the ticket flow then offers to continue
  without Repowise.

**VS Code.** VS Code reads `.mcp.json` from the workspace root by itself (the setting
`chat.mcp.workspaceRootConfig.enabled`, on by default). Open the Chat view's tools menu or run
**MCP: List Servers**, start each server, and sign in to Atlassian in the browser when asked. If the
servers don't show up there, add them by hand: Copilot settings › **MCP servers** › add each one,
with the same name, URL or command as in `.mcp.json`.

**Android Studio.**
1. In the Copilot chat, choose **Local** from the agent options (Copilot / Cloud / Local). The
   Local agent loads the app repo's `.mcp.json`; the others don't run against your machine.
2. If the servers still aren't there, add them yourself: Copilot settings › **MCP servers** › add
   each one. That file uses a slightly different layout (`servers`, with headers under
   `requestInit`); [`.github/mcp/jetbrains-mcp.example.json`](https://github.com/saraths-99/github-workflow/blob/develop/.github/mcp/jetbrains-mcp.example.json)
   in this repo has it ready to copy.
3. Sign in to Atlassian when the server says it needs authorization.

**Copilot CLI.** It reads the repo's `.mcp.json` too; servers of your own go in
`~/.copilot/mcp-config.json`.

**Signing in to Atlassian.** The browser sign-in is the default. If your company uses API tokens
instead, add `"Authorization": "Basic <base64 of email:api-token>"` as a header in your *own*
config (VS Code's user MCP settings, Android Studio's `mcp.json`) — never in the repo's `.mcp.json`,
and never commit it. The Bitbucket tools also need an Atlassian admin to turn them on for your
site.

**If something doesn't connect:**
- *"requires authorization"* — sign in to Atlassian from the server's entry in the MCP list.
- *`repowise` timed out* — Repowise isn't installed or the repo isn't indexed yet (see [Repowise](#repowise-optional)).
- *`invalid_token` for Atlassian* — the sign-in expired or was revoked. Restart the server from
  the MCP list and sign in again. While the server is stopped, the agents get none of its tools,
  including the `executeRead` and `discover` that the log download needs.
- *Atlassian worked before and now fails* — an app repo installed before 0.3.2 still points at the
  retired `https://mcp.atlassian.com/v1/sse`. Install never overwrites `.mcp.json`, so change that
  URL to `https://mcp.atlassian.com/v2/mcp` by hand.

## Your IDE at a glance

The workflow runs in three places, and they don't all support the same things. Find yours here;
the detail behind each row is in the sections named.

| | VS Code | Android Studio | Copilot CLI |
|---|---|---|---|
| **Switch on first** | Nothing | Agent Skills (Settings › GitHub Copilot › Chat › Agent; a preview feature), and choose **Local** in the agent options | Nothing |
| **MCP servers** | `.mcp.json` is read automatically | The Local agent loads `.mcp.json`; otherwise add them by hand from the example file (see [MCP servers](#mcp-servers)) | `.mcp.json`, plus your own in `~/.copilot/mcp-config.json` (see [MCP servers](#mcp-servers)) |
| **How it asks you** | `askQuestions` (click an option) | `ask_questions` (click an option) | `ask_user` |
| **Agent picker** | Only `qatalyst-ticket` shows | Only `qatalyst-ticket` shows | n/a |
| **`model:` pinning** | Works | Not confirmed; if ignored, pick the deep-tier model in the chat yourself | Not confirmed |
| **Token tracking (beta)** | Works | Skipped (VS Code only) | Skipped (VS Code only) |
| **Log download from Jira** | Not yet confirmed | Seen to fail: the agent isn't given the Atlassian `executeRead` and `discover` tools, so you save the log by hand (see below) | Not confirmed |

"Not confirmed" means the docs don't know yet, not that it fails. If you find out on a real run,
update that cell.

**VS Code**

1. Run the install (see the [install steps](https://github.com/saraths-99/github-workflow/blob/develop/README.md#2-one-time-setup)), then fill in the settings block and the two context docs.
2. Start each MCP server from **MCP: List Servers** and sign in to Atlassian when asked (see [MCP servers](#mcp-servers)).
3. To track tokens, add the one setting and reload the window (see [Token usage per ticket](#token-usage-per-ticket-beta--works-in-vs-code)).
4. Start a ticket with `/qatalyst-ticket-start <ticket ID>` or the `qatalyst-ticket` agent.

<!-- Screenshots to add: docs/images/vscode-mcp-list-servers.png, docs/images/token-report.png -->

**Android Studio**

1. Run the install (see the [install steps](https://github.com/saraths-99/github-workflow/blob/develop/README.md#2-one-time-setup)), then fill in the settings block and the two context docs.
2. Turn on Agent Skills, then choose **Local** in the Copilot chat's agent options. Without
   Agent Skills the agents run without their instructions.
3. If the MCP servers don't appear, add them from
   [`.github/mcp/jetbrains-mcp.example.json`](https://github.com/saraths-99/github-workflow/blob/develop/.github/mcp/jetbrains-mcp.example.json) and sign in
   to Atlassian (see [MCP servers](#mcp-servers)).
4. Pick the deep-tier model of the provider you installed (Claude Opus 5.5, or GPT-5.6 Sol) in the
   chat's model picker before starting, since `model:` pinning isn't confirmed here.
5. Expect no token report; review commands and edits yourself.
6. For a bug ticket with a log, download the attachment from Jira yourself into
   `.logs/<ticket ID>/raw/` (keep its file name) before the log analysis starts. On a real run, the log analyser
   reported that Android Studio gave it no `executeRead` or `discover` tool, so it couldn't download the
   attachment and asked for the file to be saved there. Once the file is there, tell it and it carries on.
7. Start a ticket the same way: `/qatalyst-ticket-start <ticket ID>` or the `qatalyst-ticket` agent.

<!-- Screenshots to add: docs/images/as-agent-skills-setting.png, docs/images/as-local-agent.png -->

**Copilot CLI**

1. Run the install (see the [install steps](https://github.com/saraths-99/github-workflow/blob/develop/README.md#2-one-time-setup)). The CLI reads `.mcp.json` by itself.
2. Start it from the app repo's root and begin a ticket with `/qatalyst-ticket-start <ticket ID>`;
   the questions come as `ask_user` prompts.

## Daily workflow

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
   reads the ticket and its Confluence pages, writes to the deterministic
   `specs/<bug|feature>/<ticket ID>/tasks.md` path, and produces one `tasks.md` — a single approval,
   not three.
3. Creates the ticket branch (`bug/<ticket ID>-<slug>` for a bug, `feature/<ticket ID>-<slug>` for a feature) from the branch you pick (it asks), then asks before moving the ticket to In
   Progress. A bug never reuses an old `feature/` branch; it gets its own `bug/` branch.
4. Runs `qatalyst-developer` through every task, then asks whether to ship now; picking "Ship it
   now" runs the shipping steps below in the same chat.

**Picking up where it stopped.** If the chat breaks, or you stop at a question, run
`/qatalyst-ticket-start <ticket ID>` again (in a new chat is fine). It works out where the ticket
is from `tasks.md` and the ticket branch: an unapproved draft goes back to the approval question,
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

**Models.** You don't pick a model, only a provider, once, when you install (see the [install steps](https://github.com/saraths-99/github-workflow/blob/develop/README.md#2-one-time-setup)). With Claude,
starting a ticket switches the chat to Claude Opus 5.5, which also runs log analysis and planning;
`qatalyst-developer` and the reviewers (security included) run on Claude Sonnet 5.5, and most test writers on Claude
Haiku 5.5. With GPT, the same three tiers run on GPT-5.6 Sol, GPT-6.1 Sol and GPT-6 Luna. Each
agent's `model:` line sets it (the full table is in [docs/workflow-design.md](../docs/workflow-design.md)
§4). Every agent runs on the chosen provider only, so your Copilot plan must include its models; if a
model isn't offered, the agent uses the next one in its list, or the chat's model. Don't switch the
chat to a cheaper model partway through: VS Code won't start a sub-agent on a model that costs more
than the chat's, and the step fails with "exceeds the current model's cost tier".

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
Once the last task is ticked, `qatalyst-developer` writes a workflow report to
`.logs/<ticket ID>/workflow-report.md`: for a bug, how many passes the log analysis took to reach
its fix; then what changed, who depends on it across the repos (the blast radius), the change risk,
and the tests around it. It tells you whether Repowise's index was used for it, and which
changed files the index had out of date (run `repowise update --working-tree`, then ask for the
report again). Without Repowise it still writes the report from direct searches and says so. It then
shows the ticket's token usage (see below), and the flow asks whether to ship now.

### Shipping

Runs as the last step of `/qatalyst-ticket-start` when you pick "Ship it now". If you picked
"Stop here, I'll ship later", run it on its own with **`/qatalyst-ticket-ship`**.

1. Confirms every task is ticked.
2. Runs `qatalyst-code-reviewer` (and `qatalyst-security-reviewer`/`qatalyst-error-handling-reviewer`
   for flagged diffs) against
   the spec.
3. Builds locally, then asks which tests to run: unit tests (the default), all tests including the
   instrumented ones (needs an emulator or device), only this ticket's tests, or none. A failing
   test stops the push; skipping tests is allowed, and the PRs then say they weren't run.
4. Asks once (push and open the PRs, or cancel), then commits, pushes, opens the Bitbucket PR,
   waits on Pipelines where it's on, and moves the ticket to In Review.

### Token usage per ticket (Beta — works in VS Code)

The workflow can report how many tokens a ticket used, split by agent and sub-agent and by model.
This feature is in beta and runs in VS Code only: in Android Studio or the Copilot CLI the workflow
skips it and creates no tracker files.
It reads only what Copilot records on your own machine; nothing is uploaded, and your prompts and
code are never recorded. Requires Python 3.9 or newer.

**Turning it on, once per machine:**

- **VS Code:** the setting `"github.copilot.chat.otel.dbSpanExporter.enabled": true`. The install
  adds it to `.vscode/settings.json` for you if that file didn't exist; otherwise add it yourself,
  in that file or your user settings. Tracking also stops if VS Code's own `telemetry.telemetryLevel`
  is `off`.

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

**How a chat gets counted for a ticket:** `/qatalyst-ticket-start` records the
ticket ID when it starts, and any chat that ran on the ticket's branch counts too. A chat
that did neither (for example, planning started from the `qatalyst-ticket` picker that you abandoned
before a branch was created) isn't counted; run
`python3 .github/token-tracker/scripts/token_tracker.py mark ABC-123` at the start of such a chat to
include it. Skills don't appear as separate rows: they make no model calls of their own.
Copilot deletes its trace data after 7 days, so run `report` (or `collect`) at least weekly on a
long-running ticket; everything it has copied stays in `.logs/token-tracker/`.
