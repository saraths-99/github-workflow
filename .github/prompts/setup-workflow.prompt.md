---
mode: agent
description: Run the Agentic AI-SDLC setup wizard for this repo (once per repo, safe to re-run).
generated-by: copilot-workflow
---

Run the `setup-workflow` skill end to end:

1. Detect whether this is a first run or a re-run (read the settings block in
   `.github/copilot-instructions.md` if present).
2. Read the context docs and the code as that skill's "Read" step describes.
3. If a context doc is missing, hand off to `setup-context-docs` and wait for the developer to
   approve the draft before continuing.
4. Ask only what the code can't show (see the skill's question bank), then show the full brief and
   wait for approval — do not generate anything before that approval.
5. Once approved, run `setup-instructions`, `setup-agents`, `setup-skills`, `setup-hooks`,
   `setup-mcp` and `setup-ticket-flow` in that order, showing a diff and asking before any
   overwrite.
6. Finish with the hand-off checklist (commit, JetBrains `mcp.json`, optional Repowise) — do none of
   those steps yourself. Also ask, once, whether to delete `.github/skills/setup-*/` and this
   prompt now that generation is done; delete only on an explicit yes, otherwise leave them.
