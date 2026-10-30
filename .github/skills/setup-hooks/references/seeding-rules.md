# Seeding rules for `sensitive-paths.txt`

The blueprint ships a baseline list (see `assets/sensitive-paths.txt`) that is never removed.
`setup-hooks` adds to it from two sources:

## From signing configs

Scan every `build.gradle.kts` for a `signingConfigs { ... }` block and pull out any
`storeFile = file("...")` (or equivalent) path. Add that exact path (not a wildcard) to the list —
a specific keystore file is worth naming precisely, not just matching by extension.

## From `.gitignore`

Scan the repo's existing `.gitignore` for lines that look credential-shaped:

- Exact names: `local.properties`, `.env`, `.env.local`, `secrets.properties`
- Extensions: `*.jks`, `*.keystore`, `*.p12`, `*.pem`, `*.key`

Add any such line to `sensitive-paths.txt` verbatim (same glob syntax). Don't add an unrelated
`.gitignore` entry (build output dirs, IDE files, etc.) just because it's present — only
credential-shaped patterns.

## Always included, regardless of repo

- `.logs/*/raw/**` — raw log captures, per the app repo layout (see the workflow's own section 3).
  This is listed in the baseline already; just confirm it's still present after merging the two
  sources above.

## What never gets added automatically

Never add a path just because a developer mentioned it was "sensitive" in passing in chat without
a specific file or glob — ask for the exact path or pattern instead. A vague entry either matches
nothing (false sense of protection) or matches too much (blocks legitimate work).
