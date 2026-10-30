---
name: setup-mcp
description: >
  Writes .github/mcp/jetbrains-mcp.example.json (token slot empty, for each
  developer to copy into their own JetBrains mcp.json) and .github/mcp.json
  (same servers, for the Copilot CLI agent mode) — but only if each one
  doesn't already exist; an existing file, this wizard's own or the
  developer's, is never touched. Then checks that Rovo MCP, Figma and
  Repowise each list tools. Run by setup-workflow as step 5.5.
generated-by: copilot-workflow
---

# setup-mcp

You run as step 5.5 of `setup-workflow`. You write config, you never write a token into the repo —
both files ship with an empty credential slot.

## 1. Write the two MCP files

For each of the two files below: **check whether it already exists in the app repo first.** If it
does — whatever its contents, whether it's one of this wizard's own earlier outputs or something
the developer wrote by hand — **skip writing it entirely.** Don't diff it, don't propose
overwriting it, don't ask; just note in the brief that it already exists and that the developer
should add `atlassian-rovo`, `figma` and `repowise` themselves if they want them and the file
doesn't already have them. This is stricter than the usual "diff and ask before overwriting" rule
the rest of `setup-workflow` follows (see its step 6) — mcp.json is where a developer is most
likely to already have their own servers configured, and a diff-and-ask gate still risks the
developer approving a merge without noticing it drops something they added. Only write either file
when it's genuinely absent.

- `.github/mcp/jetbrains-mcp.example.json` — if absent, copy `assets/mcp/jetbrains-mcp.example.json`
  here. This is a reference snippet — Copilot doesn't load it directly; each developer copies it
  into their own JetBrains `mcp.json` (opened from the chat's tools menu) and fills in their own
  Atlassian API token.
- `.github/mcp.json` — if absent, copy `assets/mcp.json` here, for the Copilot CLI agent mode. Same
  three servers, no token slot filled — CLI-mode Jira/Confluence access typically authenticates via
  an OAuth prompt at runtime rather than a static token; Bitbucket tools need the same Basic-auth
  token as JetBrains mode once the developer has one.

Never put a real token, even a placeholder that looks real, in either file.

## 2. Check each server's tools respond

By this point each file exists either way — written fresh in step 1, or already there because the
developer had their own. Confirm (where you have a live MCP connection to test against) that each
server actually lists tools. If a file was skipped in step 1 because it already existed and simply
doesn't have one or more of these three servers configured, that will show up here as "not
reachable" too — report it as "not configured in this repo's file yet," not as a broken connection.

- **Atlassian Rovo MCP** — see `references/tool-check.md` for the auth pitfalls that make this
  check return almost no tools even though the server connected.
- **Figma MCP** — confirm a basic read tool is listed.
- **Repowise** — confirm it's reachable **per repo** this app's workspace spans (see
  `references/tool-check.md` — reachable for one repo doesn't mean reachable for all of them);
  note the per-repo result in the brief and continue anyway either way (see `architecture.md`'s own
  note that it's optional).

This check can't be run from the builder repo itself — it needs a live developer environment with
real credentials — so report what you were able to confirm, and what's left for the developer to
verify after they copy their own token in.

## Safety rules for this skill

- Never write to, overwrite, or propose a diff for `.github/mcp.json` or
  `.github/mcp/jetbrains-mcp.example.json` if either already exists — check first, skip entirely if
  present, and say so in the brief. This applies on a re-run too: once either file exists, this
  skill never touches it again, even if the blueprint it was generated from later changes.
- Never write a token, even a fake-looking placeholder value, into either MCP file.
- Never silently drop the Repowise entry because it's unreachable right now — it stays in both
  files so it works the moment it's installed.
- Never merge Rovo MCP's three product surfaces (Jira, Confluence, Bitbucket) into separate config
  entries — it's one server entry with all three, per `assets/mcp/jetbrains-mcp.example.json`.
