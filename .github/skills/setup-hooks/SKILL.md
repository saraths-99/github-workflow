---
name: setup-hooks
description: >
  Writes guards.json, the four hook scripts (.sh + .ps1 each) and
  sensitive-paths.txt into .github/hooks/. Run by setup-workflow as step
  5.4. Hooks only guard and format — they never ask an agent to do work.
generated-by: copilot-workflow
---

# setup-hooks

You run as step 5.4 of `setup-workflow`. Hooks are the one mechanical enforcement layer in this
whole workflow — everything else (the specs-only rule, "run only these scripts") is a written
instruction an agent could in principle ignore. A hook can't be talked out of its decision.

## 1. Write `guards.json` and the scripts

Copy `assets/guards.json`, `assets/sensitive-paths.txt`, and every file under `assets/scripts/` into
the app repo's `.github/hooks/`, unchanged, **except** `sensitive-paths.txt`, which you re-seed per
repo (step 2). The four guards (`format-kotlin`, `block-force-push`, `protect-secrets`,
`guard-context-docs`) and their stdin/stdout contract are fixed — see `references/hook-protocol.md`
for the exact shape. Do not invent a fifth guard or change an existing one's `event` type.

## 2. Seed `sensitive-paths.txt`

Follow `references/seeding-rules.md`: scan the repo's `build.gradle.kts` signing configs for
keystore file paths, and the existing `.gitignore` for credential-shaped patterns
(`local.properties`, `.env`, `*.jks`, `*.keystore`, etc.). Always include `.logs/*/raw/**`
unconditionally — raw logs are sensitive regardless of what the repo's own `.gitignore` says. Merge
these into the blueprint's baseline list rather than replacing it; never remove a baseline entry.

## 3. Hand back to `setup-workflow`

Report the final `sensitive-paths.txt` contents in the brief summary so the developer can see
exactly what's being protected, and add anything they know is sensitive that detection missed.

## Safety rules for this skill

- Never write a guard that can approve or suppress another guard's deny.
- Never let a script change exit 0 with a silent decision — see `references/hook-protocol.md`;
  a script that errors must be allowed to fail loudly, because a script error already falls back to
  deny on its own.
- Never drop a baseline sensitive path, even if a repo's own `.gitignore` doesn't mention it.
- `format-kotlin` is the only `postToolUse` guard and therefore the only one that cannot deny
  anything — it must never be relied on to block something, only to tidy formatting after the fact.
