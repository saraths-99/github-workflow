# Changelog

All notable changes to this workflow are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/); versions follow
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), applied to the workflow itself
(agents/skills/hooks/prompts), not to any app repo it's installed into.

Bump `VERSION` and add an entry here for every change that lands in this repo — `install.sh`
reads `VERSION` and the synced commit SHA and writes both into a sync-record file in
the app repo, so this is the only place to check what an app repo is actually running and what
changed since its last sync.

## [0.6.0] - 2026-11-26

### Added
- `qatalyst-commit-message` skill: writes each repo's commit title and message from the diff,
  `tasks.md` and, for a bug, `log-analysis.md`. The title is `<ticket ID> - <imperative summary>`
  (72 characters or fewer, always starting with the ticket ID); the body gives the
  reason, the changes grouped by task and a line on tests, with no log lines, secrets or AI
  sign-off trailer. It is shown with options to rework: use it · make it shorter · add more detail ·
  change it (typed). It repeats until the developer picks "Use this message", and saves the result
  to `.logs/<ticket ID>/commit-message.md`.
- `qatalyst-ticket-ship` runs it before the commit confirmation and commits with the approved message
  only. `qatalyst-ticket-start` runs it too when the developer picks "Stop here, I'll commit later",
  so they still get a title and message to rework and use; a later `/qatalyst-ticket-ship` reuses an
  approved message while the repo's changed files are the same.
- A fix check before planning. `qatalyst-plan-ticket` now looks for three findings, each only with
  evidence it can cite: the fix is already in the code, the fix is blocked (an OS or platform
  restriction, a store policy such as Google Play's, a permission the app can't get, a limit in
  firmware, an SDK or a backend), or the evidence is too ambiguous to choose a fix (including an
  inconclusive `log-analysis.md` the code doesn't settle). A policy or platform rule it can't cite is
  treated as ambiguous, never as blocked. On a finding it asks: Do not produce a fix · Go with a fix
  anyway. It applies to bugs and features.
- "Do not produce a fix" writes `.logs/<ticket ID>/no-fix.md` (git-ignored) and ends the flow: no
  `tasks.md`, no branch, no Jira move. Running `/qatalyst-ticket-start` again shows the finding and
  asks again. "Go with a fix anyway" plans the best fix the finding allows (only what the code still
  lacks, a workaround inside the limit, or the likeliest reading with the alternatives listed), puts
  the finding first under Open questions, and `qatalyst-ticket-ship` repeats it in the commit
  message.

- `token_credits.py` in `.github/token-tracker/scripts/`: converts a ticket's `token-usage.html` (or
  `.json`) into AI credits with a model price sheet (`.xlsx`), as tokens / 1,000,000 x the model's
  USD rate, input and output priced separately, divided by $0.01 per credit, using the long-context row when a call's input is over
  the threshold. It writes `token-credits.html` and `.json` and prints a table by model and agent.
  A call whose model isn't in the sheet is listed as not priced, never guessed. The usage file has
  no cached-token split, so input is priced at the full rate. Standard library only, with tests.

### Changed
- Model tiers. Every test-related agent is now on the Fast tier (the router `qatalyst-test-writer`,
  `qatalyst-ble-protocol-test-writer` and `qatalyst-security-test-writer` moved down from Standard,
  and the `/qatalyst-write-tests` prompt with them). `qatalyst-developer` moved up to the Deep tier.
  Claude Opus 5.5 is gone from the Claude lists: Deep is now Claude Sonnet 5.5 alone, so the ticket
  chat, log analysis, planning, implementation and the code reviewer all run on it. Standard is left
  with the security and error-handling reviewers and the `/qatalyst-new-*` prompts. The code
  reviewer and the developer now share a model; the reviewer's independence comes from its fresh
  context. GPT lists are unchanged.
- Ship now runs in this order: review, token report, commit message, build and tests, one commit
  confirmation. `qatalyst-ticket-ship` shows the token report (`report --open`) once the review rounds
  are done, so it includes the review fixes and the reviewers' own calls, and then settles the
  commit message. The build, tests and commit are not in it; run `report` afterwards to add them.
  `qatalyst-ticket-start` no longer shows the report before the ship question, and
  `qatalyst-developer` still writes one quietly at the end so the workflow report can record the
  outcome. The commit message is rewritten if a later fix changes the diff.

### Added
- Token usage now carries cost and the cache split. `token-usage.json` has a new structure: ticket
  (title, type, executor from git config, start and end time), `priceUnit` USD and `totalCost`, then
  `steps` per agent with their `calls`: fresh `inputTokens`, `cachedInputTokens`, `cacheWriteTokens`,
  `outputTokens` and `totalCost`. The tracker reads three more values from Copilot's trace: cache reads,
  cache writes and Copilot's own cost per call (`copilot_usage_nano_aiu`, billionths of an AI credit, 1
  credit = $0.01). Recorded input includes the cached tokens, so the JSON's `inputTokens` is the rest.
  Calls Copilot recorded no cost for use a price sheet if one is given (`--prices` or
  `TOKEN_TRACKER_PRICES`) and are `null` otherwise. New `meta` command stores the title and type (run by
  `qatalyst-ticket-start`), `report --final` stamps `endTime` (run by `qatalyst-ticket-ship` after the
  commit). The HTML report and console summary show cost and the cache column. (`qatalyst-ticket-start`
  runs `meta` right after reading the ticket; `qatalyst-ticket-ship` runs `report --final` after the commit.)
- `qatalyst-fix-approver`: an independent approval before a ticket is committed, on GPT-5.3-Codex (a
  new `judge` tier in `models.json`, the same for both providers, so the check isn't the model family
  that wrote the fix). After the reviewers pass, `qatalyst-ticket-ship` gives it each repo's diff and
  the paths of `tasks.md`, `log-analysis.md` and the workflow report, and nothing from the developer's
  chat. It returns APPROVED or NOT APPROVED with numbered findings, judging whether the change fixes
  the cause, meets the acceptance criteria and edge cases, is proven by tests that would fail
  without it, stays in scope (an Android-only ticket needs an app fix) and leaves nothing behind. If VS Code refuses its model
  as costlier than the chat's, `qatalyst-fix-approver-fallback` runs the same check on GPT-6.1 Terra (a
  `judge-fallback` tier; a model list can't do this because VS Code checks only the first name). Both
  state their model on the first line and ship rejects an answer from a Claude model or the chat's own,
  since an agent whose model isn't in the picker silently runs on its starter's. The procedure lives in
  the `qatalyst-fix-approval` skill so the two agents can't drift. A
  NOT APPROVED is a review round in the same count of 3. Committing without approval needs "commit
  anyway, not approved" and the commit message says so; if neither approver can give an independent
  verdict, the developer is asked whether to continue without one. The verdict goes into the workflow report's "Independent
  approval" section and into the commit question. It is an exception to one provider throughout, and
  whether VS Code lets it start under a Sonnet chat has to be checked on a real run.
- Android-only tickets. When QA or the reporter says the issue is not seen on iOS ("iOS Behaviour:
  Issue is not observed in iOS"), `qatalyst-jira-ticket-intake` reports the platform scope (Android only
  · also on iOS · not stated; only a clear statement counts), and the log analyser and planner keep to
  the Android app: causes are ranked in the app, SDKs and Android platform behaviour, the suggested fix
  and the plan are app changes (workarounds for Android quirks included), and a firmware or
  cloud/backend change is never planned as the fix, even when one is possible. Odd firmware or cloud
  evidence goes under "Seen outside the app, not pursued", and the workflow report lists those areas
  as "not a fix target". Fix check: a firmware or backend limit is not a blocker on these tickets.
- The workflow report has a "Related areas that could affect the fix" section: lock firmware (BLE
  commands, OTA, model numbers), the other BLE stack, the backend, the platform and third-party or
  sibling modules, each with its evidence, why it matters and what to check or who to ask. It lists
  only areas the change, ticket or log points at, marks anything unconfirmed as "unknown, needs
  checking", and says "None found" otherwise. The chat summary gets a "Related areas:" line.
- `isLocalBuild` is `false` in everything committed. The developer keeps `isLocalBuild=true` in
  `gradle.properties` in all five repos while working; before committing, `qatalyst-ticket-ship` records
  each such line in `.logs/<ticket ID>/isLocalBuild.json`, sets it to `false` (keeping the file's
  spacing), commits, then puts every line back and deletes the record. A `gradle.properties` whose only
  change is that line isn't part of the diff or the commit message, the reviewers are told to ignore
  it, and the commit stops if `git diff --cached` still shows `isLocalBuild=true`.

### Removed
- The ship step no longer pushes, opens pull requests, reads Pipelines runs or moves the ticket to In
  Review. `qatalyst-ticket-ship` now ends at a local commit: after the review rounds, token report,
  commit message and build/tests, it asks once (commit · cancel) and commits each repo's ticket files
  (staged by name, never `git add -A`) with the approved message, then says nothing was pushed and
  names the branch for the developer to push and open the PR. `pipelines-detection.md` is deleted.
  The question labels are now "Commit it now" · "Stop here, I'll commit later"; the skill and
  prompt keep the name `qatalyst-ticket-ship`. Notes that went into PR descriptions (tests not run,
  no tests written, open review comments, a fix-check finding) now go into the commit message.
- `qatalyst-log-analyser` no longer posts a redacted comment on the Jira ticket. The analysis stays in
  `log-analysis.md`; nothing is written to Jira at that step.

## [0.5.2] - 2026-11-26

### Changed
- Token tracking setup now says that `github.copilot.chat.otel.dbSpanExporter.enabled` is not
  listed on VS Code's Settings screen (searching for it finds nothing) and goes in a settings JSON
  file. The workflow guide, the README and the design doc give the check: reload the window, send
  one Copilot chat message, and confirm `agent-traces.db` exists. They also say a ticket worked
  before the file existed reports 0 model calls and must be started again.

## [0.5.1] - 2026-11-25

### Added
- After every task is ticked, the flow asks two questions in one call: ship now, and whether the
  developer has an idea for improving the workflow. An idea is appended to
  `.logs/<ticket ID>/workflow-ideas.md` (git-ignored) with its date and ticket, and the developer is
  told its path so they can pass it on; nothing is changed or sent automatically. A re-run after a
  plan update asks again; resuming at "every task ticked" doesn't.
- A tests question at the `tasks.md` approval. The first time the draft is shown it asks, in the
  same call as the approval, whether to write tests (write, recommended · no tests for this ticket).
  "No tests" sets `**Tests:** none` in `tasks.md` (the planner applies it and removes the test parts,
  with no second approval); `qatalyst-developer` then ticks a task on a green build and skips
  `qatalyst-test-writer`, `qatalyst-code-reviewer` doesn't comment on missing tests, and
  `qatalyst-ticket-ship` drops "only this ticket's tests" and states in every PR that none were
  written. A redraft isn't asked again.
- Stuck runs. `qatalyst-developer` stops and asks (try again differently · I'll look at it ·
  restart the task · stop) after the same failure three times, a build, test or `adb` command silent
  for 10 minutes, or three passes with no progress. `qatalyst-ticket-ship` does the same for a
  silent build or test run and a Pipelines run still going after 30 minutes. A run that hangs
  outright can't report itself; the guide says to stop the chat and run `/qatalyst-ticket-start`
  again. Known gap 3 in the design doc is reworded to match.
- A review loop at ship. When `qatalyst-code-reviewer` (or the security or error-handling reviewer)
  has open comments, `qatalyst-ticket-ship` hands them to `qatalyst-developer` with a list of what was
  wrong in earlier rounds, then re-runs the reviewers, for up to 3 rounds. After round 3 it asks:
  fix by hand · ship anyway (stated in each PR) · cancel. The rounds go into the workflow report's
  "Review rounds" section. `qatalyst-code-reviewer` is pinned to the deep tier (Opus 5.5, then
  Sonnet 5.5; GPT's deep list with GPT), so the reviewer isn't the model that wrote the code.
- The workflow report now reaches the developer in every IDE. `qatalyst-developer` reads the file
  back after writing it and returns its path and full text; `qatalyst-ticket-start` shows the whole
  report in chat, under its full path, before asking whether to ship (Android Studio has no token
  report, and a sub-agent's own chat isn't always shown). The ship confirmation gives the path too.

## [0.5.0] - 2026-11-25

### Added
- A developer guide, `.github/workflow-guide.md`, is installed into the app repo. It holds the
  day-to-day parts of the README: Repowise setup, MCP servers per IDE, the per-IDE comparison, the
  daily ticket flow and token usage. The README keeps the repo overview, install and maintenance and
  points to it. `install.sh` copies it (and every install overwrites it); the manual-install list
  includes it.
- The workflow report has a "Workflow checks" section. It records how token tracking went (written,
  off, no hand-off received, or failed), which hand-off the agent received, and the Repowise index
  and commit hook status, self-reported, with "not recorded" where the agent wasn't told. The token
  report step now runs before the workflow report so the section can say how it went.
- When a token report finds no calls, it says why: no trace database found (with the paths searched),
  an empty database, calls skipped because the chat ran in another git repository, no marker for the
  ticket, or no chat linked to it.
- The Jira project is filled in from the first ticket. When `qatalyst-ticket-start` sees the placeholder
  in `jira_projects` (or no entry for the ticket's project), it adds the key from the ID the developer
  typed (`HALOM-14123` gives `HALOM`) with `bug_issue_types: [Bug]`, and corrects the key if Jira
  reports a different one. `base_branch` is left alone. `qatalyst-ticket` gets the `edit` tools for it.

### Changed
- Repowise installs with `uv tool install repowise` (was `pipx`); the guide and the ticket-start
  check say so. `install.sh` now also adds `.github/`, `.repowise/`, `.vscode/`, `docs/workflow-design.md` and
  `specs/.templates/` to the app repo's `.gitignore`, next to `.logs/`, so the installed workflow files,
  the design doc, the task template, Repowise's index and the VS Code settings stay out of the app's
  commits (a ticket's own `specs/<bug|feature>/<ticket ID>/` folder is not ignored). Files the app repo already tracks under `.github/` or
  `.vscode/` stay tracked.
- `.mcp.json` now lists only `atlassian-rovo` and `repowise`; the Figma server is dropped (the two
  planners no longer list `figma/*`, and Figma links are noted but not fetched). The Repowise entry
  runs `repowise mcp` against the folder that holds all the repos, with the full path to the
  program, and ships with two placeholders (`<USER_PATH>`, `<REPOWISE_PROJECT_PARENT_FOLDER>`) each
  developer fills in on their own machine. The guide and README say so, and the guide notes that the
  registry's `com.atlassian/atlassian-mcp-server` entry isn't seen by the agents, which look tools up
  as `atlassian-rovo/*`. Install still never overwrites an existing `.mcp.json`.
- The workflow guide records that Android Studio was seen not to give the log analyser the Atlassian
  `executeRead` and `discover` tools, so the Jira log can't be downloaded there; it says to save the
  attachment into `.logs/<ticket ID>/raw/` by hand. Not yet checked in VS Code.

### Fixed
- The Repowise check no longer uses `get_overview` as its probe. With an index built `--no-prose`
  it has no overview essay to return, so a healthy index looked unreadable. It probes with
  `search_codebase` instead, and a healthy CLI index whose MCP server isn't answering is now its own
  "not ready" case (start the MCP server) instead of "not installed".

## [0.4.9] - 2026-11-23

### Changed
- A bug no longer reuses an existing `feature/<ticket ID>-*` branch (this reverses the 0.4.6
  rule that kept it). `qatalyst-ticket-start` ignores that branch and uses a `bug/<ticket ID>-*`
  branch if one exists.
- A new ticket branch is no longer always cut from `base_branch`: `qatalyst-ticket-start` asks which
  branch to create it from (`base_branch`, the branch you're on, the old `feature/` branch's tip
  for a bug that has one with commits, or another you name). The question is in
  `qatalyst-ask-developer`'s table.
- Shipping asks which tests to run (`qatalyst-ticket-ship` step 3, row added to
  `qatalyst-ask-developer`'s table): unit tests in the modules touched, all tests including
  instrumented (checks a device is connected), only this ticket's tests, or skip. Skipping is noted
  in every PR's description, and a failing test stops the push.
- Log analysis no longer guesses when a bug ticket has a log but no issue time. Intake
  (`qatalyst-log-ticket-intake`) asks the developer for the time, or to use the whole log with no
  time window, or to stop and add it to the ticket; `qatalyst-log-analyser` trims with the time
  given, without `--at` for the whole log, or stops. The question is in `qatalyst-ask-developer`'s
  table.
- Log analysis no longer ranks a cause from an empty digest. When the trimmed log has lines but no
  warnings or errors, `qatalyst-log-analyser` asks the developer: widen the time window, use the
  whole log, report it as inconclusive, or stop. "Inconclusive" writes a short `log-analysis.md`
  stub (no cause, no fix, no Jira comment) that tells the planner to ground the cause in the code.
  The question is in `qatalyst-ask-developer`'s table.
- A workflow report: when every task is ticked, `qatalyst-developer` writes
  `.logs/<ticket ID>/workflow-report.md`. For a bug it says how many of the 5 allowed analysis passes
  it took to reach a confident fix, with a line per pass (`qatalyst-log-analyser` now counts passes
  and ends `log-analysis.md` with an "Analysis passes" section, and puts the count in its Jira
  comment; a re-run of Trim, including one the developer asks for, counts as a pass). It also holds
  the blast radius (changed files and symbols, dependents in every repo, change
  risk, tests around the change, and whether each changed file is current in Repowise's index) and
  tells the developer whether Repowise's index was used, naming stale files and the command to
  refresh them. Without Repowise it falls back to direct searches and says so. The ship
  confirmation shows the summary. Steps are in `qatalyst-repowise-lookup`.
- Token tracking runs in VS Code only. `qatalyst-ticket-start` runs `mark` only when it has the
  `vscode/askQuestions` tool, and tells the agents it hands off to "Token tracking: on" or "off";
  `qatalyst-developer` writes the token report only when told "on". In Android Studio and the Copilot
  CLI nothing is run or created.
- The developer chooses one model provider, Claude or GPT, and every agent and prompt runs on it.
  `install.sh` asks on a first install (or takes `--provider claude|gpt`, or reuses the choice kept in
  `.github/workflow-sync.md`) and `set-models.py` copies that provider's tier lists from the new
  `models.json` into each `model:` line. The files here now carry the Claude lists, so the mixed
  Claude/GPT fallback lists are gone: a plan needs the chosen provider's models. Gemini isn't offered,
  as its model names aren't known. `tests/test_set_models.py` and a static check cover the lists.
- Repowise's commit hook is installed for the developer. After the Repowise check says ready,
  `qatalyst-ticket-start` runs `repowise hook status --workspace` and `repowise hook install <repo>`
  in each repo without it (skipping a repo that has its own post-commit hook, and never using
  `--security`), so the index re-builds after every commit. It still never runs `repowise init` or
  `repowise update`.
- `qatalyst-log-analyser` is pinned to the deep tier, and `qatalyst-security-reviewer` to the standard
  tier (it ran on the chat's model before). The security reviewer is started by the code reviewer and
  the ship step, both at or above standard, so the cost rule still holds. Only the two planners are
  left unpinned.

### Removed
- The Copilot CLI launcher `.github/token-tracker/copilot-tracked.sh`, and its mentions in the docs
  and the script's messages. The script still reads a CLI trace file if one is present.

## [0.4.8] - 2026-11-23

### Changed
- Per-ticket token tracking is marked beta, confirmed to work in VS Code only. The Android Studio
  guidance is removed from its docs, and the Copilot CLI launcher (`copilot-tracked.sh`) is labelled
  untested. `README.md` and `docs/workflow-design.md` say so in the section heading.
- `README.md` has a per-IDE guide (§2d): a table of what differs between VS Code, Android Studio
  and the Copilot CLI, and a short setup checklist for each, with places marked for screenshots.

### Removed
- The four guard hooks (`.github/hooks/`: `guards.json`, the format, force-push, secret-protection
  and context-doc scripts, `sensitive-paths.txt`, `hook-protocol.md`) and `tests/test_guards.py`.
  `install.sh` no longer copies them and deletes the ones an older install left in an app repo; a
  `hooks/sensitive-paths.txt` there is left in place and can be deleted by hand. The README, the
  design doc (§6, §8, §9 and the folder tree), the instruction files, `qatalyst-new-ble-command`
  and `qatalyst-log-analyser` no longer point to a hook, and the static checks for hooks and
  `sensitive-paths.txt` are gone. The written rules in each agent stay as the only guard, and the
  design doc lists the gap in §9.

### Fixed
- Docs matched to the repo: the README's agent count (19), skill list and prompt list; the README's
  and design doc's section references; the README's 2a/2b/2c order and "three things" count;
  `docs/workflow-design.md` now shows the log-attachment download in the log-analysis loop and the
  Repowise check at ticket start.

## [0.4.7] - 2026-11-20

### Fixed
- The `/log-analyser` prompt now matches the agent: it reads the attachment list and downloads the
  log attachment with `downloadJiraIssueAttachment`. Before, it said no shell command other than the
  three log scripts could run, which ruled out the download when `/log-analyser` was run directly.
- `docs/workflow-design.md` says where VS Code reads the token-tracing setting from and how to check
  that tracing is on.

## [0.4.6] - 2026-11-19

### Fixed
- A bug ticket's branch is now `bug/<ticket ID>-<slug>`; only a feature gets `feature/<ticket ID>-<slug>`.
  Before, every ticket was branched as `feature/…`. The prefix is the same `bug`/`feature` word as the
  ticket's spec folder (including a bug chosen by the no-matching-project default), the ship step
  pushes whichever branch was created, and resuming looks for either prefix — a bug started before
  this on `feature/<ticket ID>-*` keeps that branch rather than getting a second one. "The feature
  branch" in the prose is now "the ticket branch".
- Branch slugs are kept short: lowercase kebab-case from the summary, at most 3 words and 25
  characters, filler words dropped, cut at a word boundary (`bug/HALOM-123-lock-retry-background`).
  Before, the length was unspecified, so the whole summary could end up in the name.

## [0.4.5] - 2026-11-19

### Added
- `qatalyst-ticket-start` checks Repowise before step 0 and, if it isn't ready (not installed, not
  indexed, or repos missing or behind), asks the developer to set it up, continue without it, or
  stop, with the command to fix it in the question. It never runs the install or index commands
  itself, and tells every agent it hands off to the outcome so none re-checks. The README's Repowise
  section now covers an app built from several repos: one `repowise init` from the folder that holds
  them, so lookups see callers across repos.

### Fixed
- `qatalyst-log-analyser` can now fetch a ticket's log attachment. Its `tools` lacked the Atlassian
  `executeRead` tool, which is how `downloadJiraIssueAttachment` is reached (the `atlassian-rovo/*`
  wildcard didn't expose it), so the agent reported the download tool as "not available". `tools`
  now lists `executeRead` (confirmed to work) and `discover` (not yet confirmed). The Extract step
  says to call `executeRead` with the operation name, fall back to `discover` if the server rejects
  it, and name the exact step that failed if the download can't be done.

- `qatalyst-ticket` (and so the ship step: opening the Bitbucket PRs, reading Pipelines runs, moving
  the ticket to In Review) lists `executeRead`, `executeWrite` and `discover` in `tools`. Those
  operations, and `listJiraIssueTransitions`, are only reachable through the Atlassian server's
  generic tools.
- `protect-secrets` now runs its JWT/token check on posts made through those generic tools. It used to
  decide from the tool's own name, which for `executeWrite` says nothing, so a PR description or
  comment sent that way skipped the check. Every `executeWrite`/`executeDestructive` call is now
  checked, and so is any call whose `name` argument is a write-style operation on a comment, issue,
  PR, page or description; read operations (`get…`, `list…`, `search…`, `download…`) are not.

### Changed
- `qatalyst-repowise-lookup` searches every repo in the workspace for callers, impact and change risk,
  not just the repo being edited, and an agent that falls back to direct reads says so once in its
  report, with the repos it covered.

## [0.4.4] - 2026-11-19

### Changed
- `qatalyst-ticket-start` no longer asks "treat it as a feature, treat it as a bug, or stop" when the
  ticket's Jira project isn't in `jira_projects` (or has no `bug_issue_types`). The project key and
  issue type are still read from Jira, but a ticket with no bug types to compare against now runs as
  a bug, with one line saying why — this workflow is mainly run on bugs. The question is also gone
  from `qatalyst-ask-developer`'s table.

### Fixed
- A log attached to the ticket (not pasted in a comment) is now actually fetched. Intake reads the
  attachment list with `fields: ["attachment"]` (the compact ticket view left attachments out) and
  passes the attachment id on; `qatalyst-log-analyser` downloads it with `downloadJiraIssueAttachment`
  and its returned `curl` into `.logs/<ticket ID>/raw/`. The `protect-secrets` hook allows exactly that
  `curl` (one https URL, one output file directly under `raw/`, no chaining or upload) and still
  denies every other command that names `raw/`; `tests/test_guards.py` covers both. Where the
  download can't run, the developer is told which step failed (no `discover`/`executeRead` tool, no
  download operation found, the operation's error, no terminal, or the command blocked or failed)
  and which file name to save it as. The analyser is told to run `discover` first:
  `downloadJiraIssueAttachment` isn't in the tool list, and the server only allows operations it
  listed or `discover` returned, so a model that skipped this reported the tool as "not available".

## [0.4.3] - 2026-11-17

### Added
- Edge cases are now planned and checked. `tasks-template.md` has an "Edge cases" section, each line
  tied to the task whose test covers it, drawn from the callers Repowise finds, `log-analysis.md`'s
  unexplained items and a checklist in `testing.instructions.md` (empty or null input, a boundary
  value, the same call twice, cancelled or interrupted partway, a restart mid-way, another caller of
  the same code). The unit-test writer covers them, the test router's "done" requires them, and
  `qatalyst-code-reviewer` checks every one has a test or a stated reason it can't.
- A bug is planned with a way to see it fail: its first acceptance criterion is the reported scenario
  itself, with a regression test that reproduces it (`qatalyst-bug-planner`, `qatalyst-plan-ticket`,
  `testing.instructions.md`). Where a small fix makes it practical, the test is checked to fail
  without the fix; a bug no automated test can reproduce names the manual check under Open questions.
- A green Gradle task is not treated as a passing test run where a module's build ignores test
  failures: `qatalyst-developer`, the ship step and `testing.instructions.md` say to read that module's
  test report.

## [0.4.2] - 2026-11-17

### Added
- A model per agent, in three tiers, set by `model:` in each agent's frontmatter as a list of
  `<name> (copilot)` entries tried in order, mixing Claude and GPT models. Deep: the chat's model,
  Claude Opus 5.5 (then GPT-6.1 Sol, GPT-5.6 Sol, Claude Sonnet 5.5), pinned by the `qatalyst-ticket`
  agent and the `/qatalyst-ticket-start`, `/log-analyser` and `/qatalyst-ticket-ship` prompts and
  inherited by log analysis, planning and the security review. Standard, Claude Sonnet 5.5 (then
  GPT-6.1 Sol, Claude Sonnet 5): the developer, the code and error-handling reviewers, the test
  router, and the BLE-protocol and security test writers. Fast, GPT-6 Luna (then Claude Haiku 5.5,
  GPT-5.6 Luna, Claude Haiku 4.5): log-ticket intake and the other test writers.
- The other slash-command prompts pin Sonnet 5.5, because VS Code refuses to start a sub-agent on a
  model that costs more than the chat's.
- A static check for the `model:` format, and that the user-invocable agent pins one.

### Changed
- `copilot-instructions.md`'s Model section describes the tiers instead of one model for everything.
  An app repo that already has that file keeps its old section; update it by hand.

## [0.4.1] - 2026-11-17

### Changed
- UI rule: new screens are built in Jetpack Compose; existing screens stay XML with View Binding and
  aren't converted unless a ticket says so. `xml-ui.instructions.md` (which now also applies to
  `compose/`), the `qatalyst-new-screen` skill and prompt, the key rule in `copilot-instructions.md`
  and `docs/field-sources.md` no longer say "do not introduce Compose". A Compose screen with no
  existing one to follow, or no Compose in the build, is reported as a plan mismatch rather than
  guessed at.

## [0.4.0] - 2026-11-17

### Changed
- The hooks now actually run. `guards.json` is rewritten in GitHub Copilot's native hook format
  (`hooks` keyed by `preToolUse` / `postToolUse`, `bash` command entries), which VS Code and the
  Copilot CLI load from `.github/hooks/`; before, it was in a custom format nothing ran. Android
  Studio's Copilot plugin doesn't load hook files yet.
- The four guard scripts are thin wrappers around a new `scripts/guards.py`, which reads both VS
  Code's and the CLI's payloads, prints nothing to let a call through (so the IDE's own
  confirmation still applies), and prints a `permissionDecision` to deny or ask.
- `protect-secrets` now also blocks commands naming a raw log (`cat .logs/<ticket>/raw/...`), which
  the old pattern never matched, while still letting the log analyser's `logcat_extract.py` and
  `logcat_trim.py` read them. Its token check now only applies to Jira, Confluence and PR text, so
  Kotlin code containing `token = ...` isn't blocked.
- `guard-context-docs` asks only on edits to `project-context.md` / `architecture.md`, not reads.
- `hook-protocol.md` and the static hook check describe the native format.

## [0.3.3] - 2026-11-16

### Changed
- Every agent's `tools` also lists Android Studio's own tool names (`read_file`, `list_dir`,
  `get_errors`, `grep_search`, `file_search`, `semantic_search`, `insert_edit_into_file`,
  `create_file`, `run_in_terminal`, `get_terminal_output`) for the VS Code groups it already has,
  so sub-agents started there aren't left without workspace tools. Read-only agents get only the
  read and search names. The sub-agent tool's Android Studio name is still unknown.

## [0.3.2] - 2026-11-16

### Added
- README §2c: setting up and signing in to the MCP servers in VS Code, Android Studio (choose the
  Local agent; add servers under Copilot settings › MCP servers if needed) and the Copilot CLI,
  which servers the flow needs, and what to do when one doesn't connect.

### Changed
- `atlassian-rovo` points at `https://mcp.atlassian.com/v2/mcp`, the URL Atlassian documents now;
  the old `/v1/sse` endpoint was deprecated and retired on 30 June 2026. Install doesn't overwrite
  an app repo's `.mcp.json`, so existing app repos need the URL changed by hand.
- `.github/mcp/jetbrains-mcp.example.json` uses the layout Android Studio's own `mcp.json` has
  (`servers`, headers under `requestInit`) and the new Atlassian URL.

## [0.3.1] - 2026-11-16

### Changed
- Android Studio: the agents that ask the developer list its question tool, `ask_questions` (seen
  registered in Android Studio's Copilot 1.21.0 log), so questions are clickable there too.
- Every agent sets `x-github-copilot-invoke-policy` (`["user"]` for `qatalyst-ticket`, `["model"]`
  for the rest), the field the JetBrains plugin uses to hide agents from its picker in place of
  `user-invocable`. A static check keeps the two in step.

## [0.3.0] - 2026-11-16

### Added
- `qatalyst-ask-developer` skill: every place the workflow stops for the developer is a question
  with options to click (VS Code's `vscode/askQuestions` tool, or `ask_user` in the Copilot CLI,
  including its agent inside Android Studio; numbered options in Android Studio's own Copilot chat),
  never an open-ended prompt. Requesting changes to `tasks.md` is the only
  typed answer.

### Changed
- `/qatalyst-ticket-start` (and the `qatalyst-ticket` picker agent) now carry a ticket through as
  one flow: plan approval, branch, In Progress, `qatalyst-developer` through every task, then
  "Ship it now" runs `qatalyst-ticket-ship`. `/qatalyst-ticket-ship` still works on its own.
- Running `/qatalyst-ticket-start` again on a ticket resumes it instead of starting over: an
  existing draft goes to the approval question, ticked tasks or a feature branch continue from the
  first unticked task, and all tasks ticked goes to the ship question. If the last chat broke
  partway through a task or the ship step (`.logs/<ticket ID>/in-progress.json` is still there), it
  says so and asks whether to continue keeping the changes, restart with them stashed, or stop.
- No ticket ID given: the developer's open Jira tickets are offered to pick from.
- Missing log attachment: "I've attached it now — check again" replaces re-running the command.
- Sub-agents that can't ask the developer return the question to `qatalyst-ticket-start`, which
  asks it; the planners no longer run the approval gate themselves.
- README: Android Studio needs Agent Skills turned on (a preview setting) for the ticket flow.
- `qatalyst-ticket` gains `execute` (for the branch, the token mark and pushing) and the
  `qatalyst-ticket-ship` skill.

## [0.2.1] - 2026-11-16

### Added
- README §2b: how to install Repowise and index the app repo (`repowise init --yes --no-prose
  --no-editor-setup`, then `repowise hook install`), and why editor setup must stay off.

### Removed
- `.github/log-analyser/log-signatures.md`, and `qatalyst-log-analyser`'s step that matched known
  cause chains against it. No script read it, and its noise-tag and tag-to-module tables were never
  filled in; Repowise already does the tag-to-module mapping. Install no longer adds it to app
  repos, but leaves an existing copy alone.

### Changed
- Install copies only what the workflow uses in the app repo. `.github/mcp/` (the JetBrains MCP
  snippet), `docs/field-sources.md` and `.github/hooks/hook-protocol.md` stay in this repo and are
  linked from the README and `workflow-design.md`; install removes copies an older install left.
- macOS and Linux only: removed `install.ps1`, `copilot-tracked.ps1` and the four hook scripts'
  `.ps1` versions, and their entries in `guards.json`. Re-running `install.sh` deletes the hook `.ps1` copies from app repos.

## [0.2.0] - 2026-11-16

### Added
- Per-ticket token tracking, beta (works in VS Code) (`.github/token-tracker/`): `token_tracker.py mark/collect/report`
  writes one row per model call (`ticketId`, `agentName`, `model`, `inputTokens`, `outputTokens`,
  `timestamp`) plus totals by agent and model to `.logs/token-tracker/<ticket ID>/`, as
  `token-usage.html` (self-contained page, opened in the browser by `report --open`) and
  `token-usage.json` (rows plus `totals` and `byAgent`). Reads VS Code
  Copilot Chat's local trace database and the Copilot CLI's trace file (the CLI path, started
  through `copilot-tracked.sh`, is untested). macOS and Linux only.
- `qatalyst-ticket-start` marks the ticket for tracking first; `qatalyst-developer` shows the
  ticket's token usage and opens the HTML report once every task in `tasks.md` is ticked.
- `install.sh`/`install.ps1` sync `.github/token-tracker/` and create `.vscode/settings.json` with
  the one setting tracking needs, only if the app repo has no such file.

### Changed
- `install.sh`/`install.ps1` download from the `develop` branch instead of `main`.
- README: manual-install steps for a `.zip` download (README §2a), and the `qatalyst-ticket`
  agent-picker entry point.

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
