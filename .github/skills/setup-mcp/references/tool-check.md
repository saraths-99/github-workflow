# Checking each server's tools

What "confirm the server lists tools" actually means per server, and the pitfalls specific to this
workflow's three servers.

## Atlassian Rovo MCP

- Jira and Confluence tools authenticate via OAuth — if the developer's JetBrains session isn't
  signed in to Atlassian yet, the tool list will be short or empty until they sign in once.
- The Bitbucket tools need a **scoped API token sent as Basic auth** (base64 of `email:token`), and
  an Atlassian admin must have turned on API-token auth and the Bitbucket tools in Admin Hub — if
  either is off, Bitbucket tools simply won't appear, with no error explaining why.
- **The most common failure**: a token sent as a **Bearer** token, or a classic token with broad
  scopes, returns almost no tools. If the tool list looks suspiciously short, check the auth header
  shape and the token's scopes before assuming the server itself is broken.

## Figma MCP

- Needs the developer's own Figma sign-in. A missing sign-in shows as no tools, not an error.
- Only used read-only, in the Requirements phase — don't expect or add write tools to this server's
  config.

## Repowise

- No API key, no network call for its core analysis — if it's not responding, it's very likely
  just not installed or not indexed yet for this workspace, not a config problem. See the
  `uv tool install repowise && repowise init --yes --no-prose` steps in the top-level README.
- **Check it per repo, not once for the whole workspace.** In a multi-repo setup (see `repos` in
  the settings block), Repowise can be indexed for the app repo but not a secondary SDK/firmware
  repo, or vice versa — a single pass/fail isn't safe to assume applies to every repo this app's
  agents will touch. List which of the open repos it's actually reachable/indexed for in the brief.
- Its absence for any repo is never a blocker for the rest of setup — note it per repo and move on.

## What to put in the brief

List, per server: reachable or not, and if reachable, roughly how many tools it listed (a sharp
drop from "normal" is itself a signal something's mis-scoped, even without an error message).
