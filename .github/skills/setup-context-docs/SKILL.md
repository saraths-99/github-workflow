---
name: setup-context-docs
description: >
  Drafts project-context.md and/or architecture.md when setup-workflow finds
  either missing, from the code and Repowise (when available). Never runs
  unless handed off to by setup-workflow, never touches an existing doc, and
  never writes a draft to disk before the developer approves it in chat.
generated-by: copilot-workflow
---

# setup-context-docs

You only run when `setup-workflow` hands off to you in its step 2, because one or both of
`project-context.md` and `architecture.md` is missing from the repo root. Draft only the doc(s) that
are actually missing — never touch one that already exists, even if it looks incomplete or stale.

## 1. Gather evidence

Use the same signals `setup-workflow` already gathered in its own step 1 (see
`setup-workflow/references/detection-rules.md`) plus Repowise's module map and call graph when it's
reachable. Do not re-ask the developer anything `setup-workflow` already asked.

## 2. Fill the template

Start from `assets/project-context-template.md` and/or `assets/architecture-template.md`. For every
field:

- If the evidence is solid (see `references/field-sources.md` for what counts as solid per field),
  write the fact and cite its source inline, e.g. `Koin (`AppModule.kt`)`.
- If the evidence is partial or inferred, write it but say so, e.g. `Likely Retrofit + AppSync
  (seen in \`NetworkModule.kt\`, not confirmed for every repo)`.
- If there's no evidence at all, write exactly `TBD` — never invent a plausible-sounding value.

Keep every statement traceable to a file, module, or "developer-provided note" — a reviewer should
be able to check any line against the code in under a minute.

## 3. Show the draft, wait for approval

Post the full draft in chat before writing anything. The developer may:

- Approve as-is.
- Correct specific fields (apply their correction, don't re-derive the whole doc).
- Ask you to re-check a field against the code.

**Do not write the file until this approval happens.** There is no silent-write path in this skill.

## 4. Write, once, never again

Once approved, write the file. Do not add a `generated-by: copilot-workflow` marker to
`project-context.md` or `architecture.md` themselves — once written, they belong to the developer,
and `setup-workflow` must never offer to overwrite or regenerate them on a later run. Confirm back to
`setup-workflow` which file(s) were written so it can continue its own step 2.

## Safety rules for this skill

- Never run unprompted — only on hand-off from `setup-workflow`.
- Never touch a context doc that already exists, even partially.
- Never write a draft to disk before explicit chat approval.
- Never fill a `TBD` with a guess to make the doc look more complete.
- Never cite Repowise output as fact if Repowise itself flags it as inferred/low-confidence — carry
  that caveat into the doc.
