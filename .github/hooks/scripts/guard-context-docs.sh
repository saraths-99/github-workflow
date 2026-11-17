#!/usr/bin/env bash
# preToolUse — asks before project-context.md or architecture.md is changed.
# The logic is in guards.py; see ../hook-protocol.md.
exec python3 "$(dirname "$0")/guards.py" guard-context-docs
