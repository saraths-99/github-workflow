# preToolUse — denies reads/edits of sensitive-paths.txt entries, shell commands naming them, and
# text (Jira comments, PR text) that looks like it contains a JWT or token.
$ErrorActionPreference = "Stop"

$hookDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sensitiveFile = Join-Path $hookDir "..\sensitive-paths.txt"

$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json

$patterns = @()
if (Test-Path $sensitiveFile) {
    Get-Content $sensitiveFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) { $patterns += $line }
    }
}

function Test-GlobMatch {
    param($Path, $Pattern)
    $regex = "^" + ([regex]::Escape($Pattern) -replace '\\\*\\\*', '.*' -replace '\\\*', '[^/]*') + "$"
    return $Path -match $regex -or ("/" + $Path) -match $regex
}

foreach ($p in ($payload.paths | Where-Object { $_ })) {
    foreach ($pattern in $patterns) {
        if (Test-GlobMatch $p $pattern) {
            @{ decision = "deny"; reason = "$p matches a sensitive-paths.txt entry" } | ConvertTo-Json -Compress
            exit 0
        }
    }
}

$command = $payload.command
if ($command) {
    foreach ($pattern in $patterns) {
        $stem = $pattern -replace '\*\*/', '' -replace '\*', ''
        if ($stem -and $command.Contains($stem)) {
            @{ decision = "deny"; reason = "command references a sensitive path pattern ($pattern)" } | ConvertTo-Json -Compress
            exit 0
        }
    }
}

$text = $payload.text
if ($text) {
    $jwtPattern = '\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'
    $tokenPattern = '(?i)\b(token|auth(?:orization)?|bearer|api[_-]?key|secret)\b\s*[=:]\s*\S+'
    if ($text -match $jwtPattern -or $text -match $tokenPattern) {
        @{ decision = "deny"; reason = "text contains what looks like a JWT or token" } | ConvertTo-Json -Compress
        exit 0
    }
}

@{ decision = "allow" } | ConvertTo-Json -Compress
