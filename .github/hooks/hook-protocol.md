# Hook protocol

`guards.json` is in GitHub Copilot's native hook format, so Copilot runs it directly — there's no
custom runner. Each entry calls a `.sh` in `scripts/`, which hands off to `scripts/guards.py`.

## Which IDEs run it

| IDE | Runs `.github/hooks/*.json`? |
|---|---|
| VS Code | Yes, with `chat.useHooks` on (the default). `ask` shows the normal confirmation |
| Copilot CLI | Yes. `ask` becomes `deny` in autopilot mode |
| Android Studio (Copilot plugin 1.21) | No — the plugin doesn't load hook files yet, so the agents' written rules are the only guard there |

## Config

```json
{
  "version": 1,
  "hooks": {
    "preToolUse":  [ { "type": "command", "bash": ".github/hooks/scripts/protect-secrets.sh", "timeoutSec": 30 } ],
    "postToolUse": [ { "type": "command", "bash": ".github/hooks/scripts/format-kotlin.sh", "timeoutSec": 30 } ]
  }
}
```

Commands run from the repo root. There's no `matcher`: every guard runs on every tool call and
decides for itself which calls it cares about.

## Input (stdin)

VS Code sends `{"hook_event_name", "cwd", "tool_name", "tool_input", ...}`; the Copilot CLI sends
`{"cwd", "toolName", "toolArgs", ...}`, where `toolArgs` can be a JSON string. `guards.py` accepts
both and reads, from the tool's arguments:

- **paths** — any string under a key containing `path`, `file`, `uri` or `dir`, plus the files an
  `apply_patch` names;
- **command** — the `command` argument (terminal tools);
- **text** — every other string (file content, a Jira comment, a PR description).

## Output (stdout)

- **Let the call through:** print nothing and exit 0. Never print `allow` — in VS Code that
  auto-approves the tool and skips the developer's usual confirmation.
- **Deny or ask:** print one object, carrying the decision both where the CLI reads it and where
  VS Code reads it:

```json
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "local.properties matches a sensitive-paths.txt entry, so Copilot can't touch it",
  "hookSpecificOutput": { "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..." }
}
```

## Failure modes

- **Exit 2, any other non-zero exit, or a crash** — the call is denied (fails closed).
- **Timeout** (30 seconds) — the call goes ahead through normal permissions (fails open). Every
  guard is string matching only, so this isn't hit in practice; `format-kotlin` is the one that
  runs Gradle, and it's a `postToolUse` hook that can't block anything anyway.

## The guards

| Guard | Event | Does |
|---|---|---|
| `protect-secrets` | `preToolUse` | Denies a call whose paths match `sensitive-paths.txt`, or a command naming one — except the log analyser's own `logcat_extract.py` / `logcat_trim.py` run on their own (no `;`, `&&`, `|`, `` ` `` or `$(`). Denies Jira/Confluence/PR text that looks like a JWT or token |
| `block-force-push` | `preToolUse` | Denies `git push` with `--force`, `-f` or `--force-with-lease` |
| `guard-context-docs` | `preToolUse` | Asks before an edit to, or a command naming, `project-context.md` / `architecture.md` |
| `format-kotlin` | `postToolUse` | After a `.kt`/`.kts` edit, runs `./gradlew ktlintFormat` (or `spotlessApply`) if the repo has one |
