# Tool lists per agent

Copilot agent tool lists are coarse — they grant or withhold a capability (edit, run shell
commands, which MCP servers), but can't restrict *where* an edit happens or *which* shell command
runs. So the table below is the mechanical half of each agent's scope; the written rule in the
agent's own blueprint (see `assets/agents/*.agent.md`) is the other half, and `code-reviewer` is the
backstop that actually checks the written rule was followed, on every diff.

| Agent | read | edit | search | run commands | MCP servers | Written scope rule |
|---|---|---|---|---|---|---|
| `log-analyser` | yes | yes | yes | yes, restricted in its own instructions to `logcat_extract.py` / `logcat_trim.py` / `logcat_digest.py` only, in that order | Atlassian Rovo (Jira read + comment), Repowise | May write only `specs/<feature>/<ticket>/log-analysis.md`; may read `.logs/<ticket>/trimmed.log` and `digest.md`, never `.logs/<ticket>/raw/` or `.logs/<ticket>/raw/extracted/` |
| `ticket-analyst` | yes | yes | yes | no | Atlassian Rovo (Jira, Confluence), Figma (read-only), Repowise | May write only `specs/<feature>/<ticket>/requirements.md` |
| `architect` | yes | yes | yes | no | Repowise | May write only `specs/<feature>/<ticket>/design.md` and `tasks.md` |
| `developer` | yes | yes | yes | yes (build/test commands) | Repowise | May edit production code and tests only for the task currently in progress in `tasks.md`; must tick the task when done |
| `test-writer` | yes | yes | yes | yes (test commands) | Repowise | May edit only test files for the task `developer` just implemented |
| `code-reviewer` | yes | no | yes | no | Repowise | Read-only: posts review comments, never edits code; checks every other agent's specs-only rule on each diff |
| `security-reviewer` | yes | no | yes | no | Repowise | Read-only: reviews only diffs touching tokens, SQLCipher, Tink, BLE secure channels or permissions; never edits code |

## Why reviewers get no edit tool

Removing `edit` from the tool list is the one scope rule Copilot *can* enforce mechanically — so
both reviewers have it removed outright, instead of relying on a written instruction alone.

## Why `log-analyser`'s run-commands scope is written, not mechanical

Copilot has no per-command allowlist in a tool list — "can run commands" is all-or-nothing. So
`log-analyser`'s blueprint states explicitly that it may only invoke the three named scripts, and
`code-reviewer` isn't the backstop here (log-analyser's phase is before any code diff exists); the
backstop is the developer reviewing `log-analysis.md` and the redacted Jira comment it posts, per
the Report step in the log-analysis loop.
