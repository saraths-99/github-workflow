# Copies the setup-* skills and the /setup-workflow prompt from this builder repo
# into an app repo's .github/, so its developer can run /setup-workflow in Android
# Studio. Writes nothing under ~/.copilot/, and never touches the app repo's
# .agents/, .claude/, .android-studio/ or AGENTS.md.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$AppRepoPath
)

$ErrorActionPreference = "Stop"

$BuilderDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $AppRepoPath -PathType Container)) {
    Write-Error "error: '$AppRepoPath' is not a directory"
    exit 1
}
$AppRepo = (Resolve-Path -LiteralPath $AppRepoPath).Path

$SrcSkills = Join-Path $BuilderDir ".github\skills"
$SrcPrompt = Join-Path $BuilderDir ".github\prompts\setup-workflow.prompt.md"
$DstSkills = Join-Path $AppRepo ".github\skills"
$DstPrompts = Join-Path $AppRepo ".github\prompts"

New-Item -ItemType Directory -Force -Path $DstSkills | Out-Null
New-Item -ItemType Directory -Force -Path $DstPrompts | Out-Null

$copiedAny = $false
Get-ChildItem -Path $SrcSkills -Directory -Filter "setup-*" -ErrorAction SilentlyContinue | ForEach-Object {
    $dest = Join-Path $DstSkills $_.Name
    if (Test-Path -LiteralPath $dest) {
        Remove-Item -LiteralPath $dest -Recurse -Force
    }
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse
    Write-Host "copied skill: $($_.Name)"
    $copiedAny = $true
}

if (-not $copiedAny) {
    Write-Warning "no setup-* skills found under $SrcSkills (builder repo not yet past phase 1)"
}

if (Test-Path -LiteralPath $SrcPrompt) {
    Copy-Item -LiteralPath $SrcPrompt -Destination (Join-Path $DstPrompts "setup-workflow.prompt.md") -Force
    Write-Host "copied prompt: setup-workflow.prompt.md"
} else {
    Write-Warning "$SrcPrompt not found yet (builder repo not yet past phase 2)"
}

Write-Host "done. Open '$AppRepo' in Android Studio and run /setup-workflow in Copilot chat."
