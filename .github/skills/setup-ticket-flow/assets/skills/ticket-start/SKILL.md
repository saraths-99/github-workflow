---
name: ticket-start
description: >
  /ticket-start <ticket ID>. The single entry point for any ticket, from any
  of this repo's configured Jira projects — detects whether it's a bug from
  its Jira issue type (checked against whichever configured project the
  ticket actually belongs to) and runs log-analyser first if so, with no
  separate manual step required. Then reads the ticket, its Confluence and
  Figma links and the matching workflow doc, and drives requirements, design
  and tasks through ticket-analyst and architect, each approved by the
  developer, before creating feature branches and asking before moving the
  ticket to In Progress.
jira_projects: <JIRA_PROJECTS_LIST>
base_branch: <BASE_BRANCH>
repos: <REPO_LIST>
generated-by: copilot-workflow
---

# ticket-start

Run at the start of every ticket — this is the only command a developer needs to remember,
regardless of whether the ticket turns out to be a bug or a feature. You decide that yourself, in
step 0, rather than relying on the developer to know and to run `/log-analyser` separately first.

You orchestrate Requirements, Design and Tasks — you don't write any of the three spec files
yourself; that's `ticket-analyst` and `architect`. You don't run the log-analysis loop yourself
either; that's `log-analyser`.

## 0. Detect whether this is a bug

`<JIRA_PROJECTS_LIST>` is a list, one entry per Jira project this repo's tickets can come from —
read from `copilot-instructions.md`'s settings block (`jira_projects`), same values
`setup-workflow` asked for at setup time. Each entry has its own `key` and `bug_issue_types`; a
multi-repo workspace commonly tracks different repos under different projects, each with its own
issue-type scheme, so there's no single shared `bug_issue_types` to check against.

1. Read the ticket's Jira `issuetype` field **and its project key** via Atlassian Rovo MCP — read
   the project key from the ticket's own Jira data, never parsed from the ticket ID string.
2. Match that project key against `<JIRA_PROJECTS_LIST>`. If none matches, **stop and ask the
   developer** — this is a ticket from a Jira project this repo hasn't been configured for; don't
   guess which entry's `bug_issue_types` to fall back to.
3. Compare the ticket's `issuetype` against *that matched project's* `bug_issue_types`.
4. **If it matches a bug type:**
   - If `specs/<feature>/<ticket ID>/log-analysis.md` already exists, skip straight to step 2 below
     — it's already been analyzed (via a manual `/log-analyser` run, or a previous pass of this
     same step).
   - Otherwise, hand off to the `log-analyser` agent yourself, exactly as `/log-analyser <ticket ID>`
     would, and wait for it to finish and write `log-analysis.md` before continuing.
5. **If it doesn't match a bug type**, skip the log-analysis phase entirely and go straight to
   step 1 below.

A developer can still run `/log-analyser <ticket ID>` manually and ahead of time if they want to
look at the logs before deciding to start the ticket at all — in that case step 0.4's "already
exists" branch just picks it up.

## 1. Read

Read the Jira ticket (whichever of `<JIRA_PROJECTS_LIST>` it matched in step 0), its linked
Confluence pages and Figma designs, and the workflow doc matching its feature area.

## 2. Feature folder

If `log-analysis.md` exists for this ticket (step 0), reuse the feature folder it's already in —
don't ask again. For a bug, this is always the case by this point (step 0 forces `log-analyser` to
run first, and it never offers to create a new folder on its own — see its own scope rules), so
the "otherwise" branch below only ever applies to a feature ticket.

Otherwise, **ask the developer** which feature this ticket belongs to — don't derive a name
yourself from the ticket's title and present it as settled:

1. List the existing `specs/*/` folder names, in case this ticket belongs to one of them.
2. If none fit, ask them to name the new feature folder. Only once they've given a name, create
   `specs/<name>/<ticket ID>/`.

A title- or component-derived slug is a guess, not something the developer chose — asking costs one
message and avoids a feature folder with a name nobody actually picked.

## 3. Requirements, design, tasks

1. Hand off to `ticket-analyst` for `requirements.md`. For a bug, it folds in `log-analysis.md`'s
   root cause and suggested fix rather than re-deriving them. Wait for developer approval before
   continuing.
2. Hand off to `architect` for `design.md`, then `tasks.md`. Wait for developer approval after each.

## 4. Branches

Once `tasks.md` is approved, create `feature/<ticket ID>-<slug>` in every repo `design.md` names as
touched, branched from `<BASE_BRANCH>` (or the per-repo base if a repo's own default differs — ask
if `design.md` doesn't say). Repos for this app: `<REPO_LIST>`.

## 5. Transition

Ask the developer before moving the Jira ticket to In Progress — don't transition it silently.

## Sizing

A one-line fix still goes through this flow, just with a short `requirements.md` and a single task
— don't skip the approval gates, and don't skip step 0's detection, even for a small ticket.

## Rules

- Never guess at the ticket's type from its title or description — step 0 reads the actual Jira
  `issuetype` field; a title that happens to contain the word "bug" is not the signal.
- Never write to `log-analysis.md`, `requirements.md`, `design.md` or `tasks.md` yourself — only
  `log-analyser`, `ticket-analyst` and `architect` do, and only inside
  `specs/<feature>/<ticket ID>/`.
- Never create a feature branch before `tasks.md` is approved.
- Never move the Jira ticket's status without asking first.
- If a ticket's project key doesn't match any entry in `jira_projects`, or the matched entry's
  `bug_issue_types` is empty, stop and ask the developer — don't silently treat it as a feature or
  borrow another project's `bug_issue_types` as a fallback.
