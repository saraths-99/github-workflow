# Hook protocol

The exact contract every guard script in `assets/scripts/` follows, so `guards.json` can invoke any
of them the same way regardless of what the guard checks.

## Invocation

The host calls the guard's `.sh` (or `.ps1` on Windows) with a single JSON object on **stdin**:

```json
{
  "event": "preToolUse",
  "tool": "edit",
  "paths": ["app/src/main/.../LoginFragment.kt"],
  "command": null,
  "text": null
}
```

- `event` — `"preToolUse"` or `"postToolUse"`.
- `tool` — the tool being called (`read`, `edit`, `runCommands`, or an MCP tool name).
- `paths` — file paths the call touches, if any; `[]` or omitted otherwise.
- `command` — the shell command text, only set when `tool` is `runCommands`.
- `text` — free text being written (a Jira comment, a PR description), only set for tools that post
  text content.

## Response

The script writes exactly one JSON object to **stdout** and exits `0`:

```json
{"decision": "allow"}
{"decision": "deny", "reason": "local.properties is a protected path"}
{"decision": "ask", "reason": "this edits architecture.md"}
```

- `allow` — proceed.
- `deny` — block the action; the host shows `reason` to the developer.
- `ask` — the host prompts the developer before proceeding, if the current agent mode supports an
  interactive ask; if it doesn't, the host treats `ask` as `deny` (per `guard-context-docs.sh`'s own
  note).

## Failure modes

- **Non-zero exit, or no valid JSON on stdout** — the host treats this as an error and denies the
  action. A guard script should let a genuine internal error propagate (non-zero exit) rather than
  swallow it into a false `allow`.
- **Timeout** — 30 seconds by default. A timed-out guard falls back to normal permissions (as if the
  guard weren't installed) — this is a host behavior, not something the script controls. Keep every
  guard's own logic fast (string/glob matching only; no network calls) so this path is never hit in
  practice.

## `postToolUse` can't deny

`format-kotlin` is the only `postToolUse` guard. Its `decision` field is only ever `"allow"` — the
event has already happened by the time a `postToolUse` guard runs. Its real job is the side effect
(running the formatter), not the decision.
