#!/usr/bin/env bash
# Starts the Copilot CLI with token tracking on, for one ticket. Use it in place of `copilot`,
# e.g. from Android Studio's terminal:
#   .github/token-tracker/copilot-tracked.sh ABC-123 [any copilot arguments]
# Writes the CLI's trace (names, models, token counts, timings; never prompt or code content) to
# .logs/token-tracker/copilot-cli-otel.jsonl, which token_tracker.py reads.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <ticket ID> [copilot arguments...]" >&2
  exit 1
fi
TICKET="$1"
shift

ROOT="$(git rev-parse --show-toplevel)"
python3 "$ROOT/.github/token-tracker/scripts/token_tracker.py" mark "$TICKET"

export COPILOT_OTEL_ENABLED=true
export COPILOT_OTEL_EXPORTER_TYPE=file
export COPILOT_OTEL_FILE_EXPORTER_PATH="$ROOT/.logs/token-tracker/copilot-cli-otel.jsonl"
export COPILOT_OTEL_CAPTURE_CONTENT=false
exec copilot "$@"
