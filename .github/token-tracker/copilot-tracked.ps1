# Starts the Copilot CLI with token tracking on, for one ticket. Use it in place of `copilot`,
# e.g. from Android Studio's terminal:
#   .github\token-tracker\copilot-tracked.ps1 ABC-123 [any copilot arguments]
# Writes the CLI's trace (names, models, token counts, timings; never prompt or code content) to
# .logs\token-tracker\copilot-cli-otel.jsonl, which token_tracker.py reads.

if ($args.Count -lt 1) {
    Write-Error "usage: copilot-tracked.ps1 <ticket ID> [copilot arguments...]"
    exit 1
}
$Ticket = $args[0]
$CopilotArgs = @($args | Select-Object -Skip 1)

$ErrorActionPreference = "Stop"
$Root = (git rev-parse --show-toplevel).Trim()
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
& $Python (Join-Path $Root ".github\token-tracker\scripts\token_tracker.py") mark $Ticket
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:COPILOT_OTEL_ENABLED = "true"
$env:COPILOT_OTEL_EXPORTER_TYPE = "file"
$env:COPILOT_OTEL_FILE_EXPORTER_PATH = Join-Path $Root ".logs\token-tracker\copilot-cli-otel.jsonl"
$env:COPILOT_OTEL_CAPTURE_CONTENT = "false"
& copilot @CopilotArgs
exit $LASTEXITCODE
