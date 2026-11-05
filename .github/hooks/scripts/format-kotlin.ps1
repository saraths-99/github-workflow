# postToolUse — never denies. Formats the edited file if the repo has a Kotlin formatter wired up.
$ErrorActionPreference = "Stop"

$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
$path = $null
if ($payload.paths -and $payload.paths.Count -gt 0) { $path = $payload.paths[0] }

if ($path -and ($path -like "*.kt" -or $path -like "*.kts")) {
    $repoRoot = (git rev-parse --show-toplevel 2>$null)
    if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
    $gradlew = Join-Path $repoRoot "gradlew.bat"
    if (Test-Path $gradlew) {
        Push-Location $repoRoot
        try {
            & $gradlew ktlintFormat -q 2>$null
            if ($LASTEXITCODE -ne 0) { & $gradlew spotlessApply -q 2>$null }
        } catch {
            # formatting is best-effort; never block on failure
        } finally {
            Pop-Location
        }
    }
}

@{ decision = "allow" } | ConvertTo-Json -Compress
