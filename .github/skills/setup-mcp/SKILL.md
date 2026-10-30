---
name: setup-mcp
description: >
  Writes .github/mcp/jetbrains-mcp.example.json (token slot empty, for each
  developer to copy into their own JetBrains mcp.json) and .github/mcp.json
  (same servers, for the Copilot CLI agent mode). Then checks that Rovo MCP,
  Figma and Repowise each list tools. Run by setup-workflow as step 5.5.
generated-by: copilot-workflow
---

# setup-mcp

You run as step 5.5 of `setup-workflow`. You write config, you never write a token into the repo —
both files ship with an empty credential slot.

## 1. Write the two MCP files

- Copy `assets/mcp/jetbrains-mcp.example.json` to the app repo's `.github/mcp/jetbrains-mcp.example.json`.
  This is a reference snippet — Copilot doesn't load it directly; each developer copies it into
  their own JetBrains `mcp.json` (opened from the chat's tools menu) and fills in their own
  Atlassian API token.
- Copy `assets/mcp.json` to the app repo's `.github/mcp.json`, for the Copilot CLI agent mode. Same
  three servers, no token slot filled — CLI-mode Jira/Confluence access typically authenticates via
  an OAuth prompt at runtime rather than a static token; Bitbucket tools need the same Basic-auth
  token as JetBrains mode once the developer has one.

Never put a real token, even a placeholder that looks real, in either file.

## 2. Check each server's tools respond

Once both files exist, confirm (where you have a live MCP connection to test against) that each
server actually lists tools:

- **Atlassian Rovo MCP** — see `references/tool-check.md` for the auth pitfalls that make this
  check return almost no tools even though the server connected.
- **Figma MCP** — confirm a basic read tool is listed.
- **Repowise** — confirm it's reachable; if not, note in the brief that Repowise is unavailable and
  continue anyway (see `architecture.md`'s own note that it's optional).

This check can't be run from the builder repo itself — it needs a live developer environment with
real credentials — so report what you were able to confirm, and what's left for the developer to
verify after they copy their own token in.

## Safety rules for this skill

- Never write a token, even a fake-looking placeholder value, into either MCP file.
- Never silently drop the Repowise entry because it's unreachable right now — it stays in both
  files so it works the moment it's installed.
- Never merge Rovo MCP's three product surfaces (Jira, Confluence, Bitbucket) into separate config
  entries — it's one server entry with all three, per `assets/mcp/jetbrains-mcp.example.json`.
