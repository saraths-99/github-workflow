#!/usr/bin/env bash
# preToolUse — denies a git push with --force, -f or --force-with-lease.
# The logic is in guards.py; see ../hook-protocol.md.
exec python3 "$(dirname "$0")/guards.py" block-force-push
