# preToolUse — asks the developer before project-context.md or architecture.md is touched;
# the host treats "ask" as "deny" if the current agent mode doesn't support asking.
$ErrorActionPreference = "Stop"

$payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
$guarded = @("project-context.md", "architecture.md")

$hit = $false
foreach ($p in ($payload.paths | Where-Object { $_ })) {
    if ($guarded -contains (Split-Path $p -Leaf)) { $hit = $true }
}
if (-not $hit -and $payload.command) {
    foreach ($name in $guarded) {
        if ($payload.command.Contains($name)) { $hit = $true }
    }
}

if ($hit) {
    @{
        decision = "ask"
        reason = "this touches a context doc (project-context.md/architecture.md); confirm with the developer first. If this agent mode doesn't support ask, treat as deny."
    } | ConvertTo-Json -Compress
} else {
    @{ decision = "allow" } | ConvertTo-Json -Compress
}
