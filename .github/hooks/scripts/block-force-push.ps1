# preToolUse — denies a shell command that force-pushes.
$ErrorActionPreference = "Stop"

$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
$command = $payload.command
if (-not $command) { $command = "" }

$hasPush = $command -match "\bgit\b.*\bpush\b"
$hasForce = $command -match "(--force\b|--force-with-lease\b|(?<!\S)-f(?!\S))"

if ($hasPush -and $hasForce) {
    @{ decision = "deny"; reason = "git push --force (or -f/--force-with-lease) is blocked by block-force-push" } | ConvertTo-Json -Compress
} else {
    @{ decision = "allow" } | ConvertTo-Json -Compress
}
