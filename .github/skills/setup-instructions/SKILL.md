---
name: setup-instructions
description: >
  Writes .github/copilot-instructions.md and the path-specific instruction
  files under .github/instructions/, run by setup-workflow after the brief is
  approved. Only writes the path files whose stack signal was actually
  detected; copilot-instructions.md itself is always written and holds the
  settings block, module map, key rules and links to the context docs.
generated-by: copilot-workflow
---

# setup-instructions

You run as step 5.1 of `setup-workflow`, after the brief is approved. Everything you write carries
a `generated-by: copilot-workflow` marker and is safe for `setup-workflow` to re-generate and diff
on a later run — except `project-context.md` and `architecture.md`, which you only ever *link to*,
never copy from or write to.

## 1. Write `copilot-instructions.md`

Always write this file, from `assets/copilot-instructions-template.md`, filling in:

- **Settings block** — `jira_projects` (one entry per Jira project this repo's tickets can come
  from, each with its own `key` and `bug_issue_types` — issue-type schemes are per-Jira-project, not
  per-repo) and `base_branch`, from the approved brief (see
  `setup-workflow/references/question-bank.md` for where these came from). This is the exact block
  `setup-workflow` reads back on a re-run — don't change its shape.
- **Module map** — one line per module from the module graph `setup-workflow` detected (its step 1),
  not the full dependency detail already in `architecture.md` — just enough to route a task to the
  right repo and module at a glance.
- **Key rules** — a short bullet summary of the architecture rules from `architecture.md` (layers,
  UI approach, DI, module boundaries, error handling, storage) — a pointer, not a copy. Keep this
  whole file small; anything more than a summary belongs in a path instruction file or in
  `architecture.md` itself.
- **Links** — relative links to `project-context.md`, `architecture.md`, `workflow.prompt.md` and
  `docs/workflows/` if they exist. Never inline their content.

## 2. Write the path instruction files that apply

Each file under `assets/` maps to one stack signal in `references/detection-map.md`. Write only the
files whose signal `setup-workflow`'s detection step actually found in this repo — do not write a
BLE instruction file into a repo with no BLE stack, for example. `references/detection-map.md` lists
the condition for each of the eight blueprint files:

| File | Written when |
|---|---|
| `kotlin.instructions.md` | Always (Kotlin is the baseline for v1's supported repos) |
| `xml-ui.instructions.md` | XML layouts + View Binding detected |
| `koin-di.instructions.md` | Koin detected |
| `ble-halo.instructions.md` | A Halo-named BLE package detected |
| `ble-gdo.instructions.md` | A GDO-named BLE package detected |
| `data-layer.instructions.md` | A repository/service layer detected |
| `testing.instructions.md` | Always |
| `gradle.instructions.md` | Always |

Each written file keeps the blueprint's `applyTo` glob unchanged — these globs are deliberately
generic (`**/*.kt`, `**/layout/**`, etc.) so they work whichever modules match, without per-repo
editing.

## 3. Hand back to `setup-workflow`

Report which files were written (and which path files were skipped, and why) so the brief's
"what was generated" summary and the step-6 diff review both reflect reality.

## Safety rules for this skill

- Never write or edit `project-context.md`, `architecture.md`, `workflow.prompt.md` or anything
  under `docs/workflows/` — link only.
- Never write a path instruction file for a stack signal that wasn't actually detected.
- Never shrink or hand-edit `copilot-instructions.md`'s settings block format — `setup-workflow`'s
  re-run detection depends on its exact shape.
- Keep `copilot-instructions.md` itself short; if it's growing past a settings block + module map +
  a short rules summary + links, that detail belongs in a path instruction file instead.
