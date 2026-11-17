#!/usr/bin/env bash
# preToolUse — denies reads, edits and commands naming a sensitive-paths.txt entry, and posted text that looks like a token.
# The logic is in guards.py; see ../hook-protocol.md.
exec python3 "$(dirname "$0")/guards.py" protect-secrets
