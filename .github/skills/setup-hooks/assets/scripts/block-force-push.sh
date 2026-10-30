#!/usr/bin/env bash
# preToolUse — denies a shell command that force-pushes.
set -euo pipefail

python3 -c "$(cat <<'PYEOF'
import json, re, sys

data = json.load(sys.stdin)
command = data.get("command") or ""

has_push = re.search(r"\bgit\b.*\bpush\b", command) is not None
has_force = re.search(r"(--force\b|--force-with-lease\b|(?<!\S)-f(?!\S))", command) is not None

if has_push and has_force:
    print(json.dumps({
        "decision": "deny",
        "reason": "git push --force (or -f/--force-with-lease) is blocked by block-force-push",
    }))
else:
    print(json.dumps({"decision": "allow"}))
PYEOF
)"
