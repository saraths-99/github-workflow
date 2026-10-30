#!/usr/bin/env bash
# preToolUse — asks the developer before project-context.md or architecture.md is touched;
# the host treats "ask" as "deny" if the current agent mode doesn't support asking.
set -euo pipefail

python3 -c "$(cat <<'PYEOF'
import json
import os
import sys

data = json.load(sys.stdin)
guarded = {"project-context.md", "architecture.md"}

hit = any(os.path.basename(p) in guarded for p in (data.get("paths") or []))
if not hit:
    command = data.get("command") or ""
    hit = any(name in command for name in guarded)

if hit:
    print(json.dumps({
        "decision": "ask",
        "reason": (
            "this touches a context doc (project-context.md/architecture.md); confirm with the "
            "developer first. If this agent mode doesn't support ask, treat as deny."
        ),
    }))
else:
    print(json.dumps({"decision": "allow"}))
PYEOF
)"
