#!/usr/bin/env bash
# preToolUse — denies reads/edits of sensitive-paths.txt entries, shell commands naming them, and
# text (Jira comments, PR text) that looks like it contains a JWT or token.
set -euo pipefail

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sensitive_file="$hook_dir/../sensitive-paths.txt"

python3 -c "$(cat <<'PYEOF'
import fnmatch
import json
import re
import sys

sensitive_file = sys.argv[1]
data = json.load(sys.stdin)

patterns = []
try:
    with open(sensitive_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
except FileNotFoundError:
    pass


def matches_any(path):
    return any(
        fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, "*/" + p) for p in patterns
    )


def deny(reason):
    print(json.dumps({"decision": "deny", "reason": reason}))
    sys.exit(0)


for p in data.get("paths") or []:
    if matches_any(p):
        deny(f"{p} matches a sensitive-paths.txt entry")

command = data.get("command") or ""
if command:
    for p in patterns:
        stem = p.replace("**/", "").replace("*", "")
        if stem and stem in command:
            deny(f"command references a sensitive path pattern ({p})")

text = data.get("text") or ""
if text:
    jwt_re = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
    token_re = re.compile(r"(?i)\b(token|auth(?:orization)?|bearer|api[_-]?key|secret)\b\s*[=:]\s*\S+")
    if jwt_re.search(text) or token_re.search(text):
        deny("text contains what looks like a JWT or token")

print(json.dumps({"decision": "allow"}))
PYEOF
)" "$sensitive_file"
