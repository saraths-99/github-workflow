#!/usr/bin/env bash
# postToolUse — formats Kotlin after a .kt/.kts edit; never blocks.
# The logic is in guards.py; see ../hook-protocol.md.
exec python3 "$(dirname "$0")/guards.py" format-kotlin
