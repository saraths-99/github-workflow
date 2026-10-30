---
name: setup-agents
description: >
  Writes the seven agents into .github/agents/, the log-analyser's scripts
  (extract, trim, digest) and log-signatures.md into .github/log-analyser/,
  the /log-analyser prompt, and adds .logs/ to .gitignore. Run by
  setup-workflow as step 5.2, after setup-instructions has written the rules
  these agents point to.
generated-by: copilot-workflow
---

# setup-agents

You run as step 5.2 of `setup-workflow`, after `setup-instructions` has written
`copilot-instructions.md` and the path instruction files. Every agent you write links back to those
files rather than repeating their rules.

## 1. Write the seven agents

Copy each file under `assets/agents/` to the app repo's `.github/agents/`, as-is except for two
substitutions:

- Fill in the module map / repo list from the approved brief, wherever a blueprint says
  `<MODULE_MAP>`.
- If a stack signal an agent depends on wasn't detected (see `setup-instructions`'s
  `detection-map.md` — e.g. no GDO package found), remove that agent's references to the missing
  area rather than leaving a dangling pointer to an instruction file that doesn't exist. Never
  remove an agent entirely — all seven are always written, even if one of their referenced areas is
  thin for this repo.

Each blueprint already carries the scope rules from `references/tool-lists.md` in its own text —
Copilot's tool lists can't enforce "specs only" or "log scripts only" mechanically, so these rules
live in the agent's own instructions, and `code-reviewer`'s blueprint already includes the check for
the specs-only rule on every diff it reviews.

## 2. Write the log-analyser's scripts and seed file

- Copy `assets/log-analyser/scripts/logcat_extract.py`, `logcat_trim.py` and `logcat_digest.py`
  verbatim to the app repo's `.github/log-analyser/scripts/`. These are plain Python 3 with no AI
  calls and no modification per repo — testers run them standalone exactly as shipped.
- Write `.github/log-analyser/log-signatures.md` from `assets/log-analyser/log-signatures-template.md`,
  but seed its "Tag → module map" section for real: scan the repo for `Log.d`/`Log.e`/`Log.w` call
  sites, collect each literal tag string, and map it to the module/package it was found in. Leave
  "Known cause chains" as the template's placeholder — those are only added later, by the developer,
  after a bug is confirmed fixed (see the template's own note).

## 3. Write the `/log-analyser` prompt

Copy `assets/prompts/log-analyser.prompt.md` to the app repo's `.github/prompts/log-analyser.prompt.md`
unchanged.

## 4. Add `.logs/` to `.gitignore`

If the app repo has a `.gitignore`, append a `.logs/` line only if it isn't already covered by an
existing pattern. If there's no `.gitignore`, create one containing just that line. Never touch any
other line in an existing `.gitignore`.

## Safety rules for this skill

- Never invent a module map or repo list — use only what's in the approved brief.
- Never modify `logcat_extract.py`, `logcat_trim.py` or `logcat_digest.py` per repo; a fix to any of
  the three belongs in this skill's own blueprint, not in a generated copy.
- Never pre-fill "Known cause chains" in `log-signatures.md` with a guess — only the tag-to-module
  map is seeded from real code; cause chains are learned later, from a confirmed fix.
- Never grant an agent a tool or MCP server it doesn't need — see `references/tool-lists.md` for
  the exact list per agent.
