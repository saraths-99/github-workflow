#!/usr/bin/env bash
# postToolUse — never denies. Formats the edited file if the repo has a Kotlin formatter wired up.
set -euo pipefail

path="$(python3 -c "$(cat <<'PYEOF'
import json, sys
data = json.load(sys.stdin)
paths = data.get("paths") or []
print(paths[0] if paths else "")
PYEOF
)")"

if [ -n "$path" ] && [[ "$path" == *.kt || "$path" == *.kts ]]; then
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  if [ -x "$repo_root/gradlew" ]; then
    ( cd "$repo_root" && ./gradlew ktlintFormat -q ) >/dev/null 2>&1 \
      || ( cd "$repo_root" && ./gradlew spotlessApply -q ) >/dev/null 2>&1 \
      || true
  fi
fi

echo '{"decision": "allow"}'
