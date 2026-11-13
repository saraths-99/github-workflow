# Installs/updates the Agentic AI-SDLC workflow from this repo into an app repo.
#
# Usage, from inside the app repo (the common case):
#   irm https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.ps1 | iex
#
# Or, with a local checkout of this repo:
#   \path\to\github-workflow\install.ps1 [-Target <target-repo-path>]   # defaults to the current directory
#
# See install.sh for exactly what gets synced vs. preserved. Writes .github\workflow-sync.md every
# run (version, commit, timestamp) -- see this repo's CHANGELOG.md for what changed since.
#
# Can't run this script at all (no shell, or this repo is only a downloaded .zip)? See README.md
# §2a for exactly which files to copy by hand instead -- don't just copy the whole extracted
# folder into the app repo.

param(
    [string]$Target = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/saraths-99/github-workflow.git"
$Branch = "develop"

$Target = (Resolve-Path $Target).Path
git -C $Target rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "$Target is not a git repo. Run this from inside the app repo you want to install into."
    exit 1
}

$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid())
New-Item -ItemType Directory -Path $Tmp | Out-Null
try {
    Write-Host "Downloading $RepoUrl@$Branch ..."
    $Src = Join-Path $Tmp "src"
    git clone --depth 1 --branch $Branch --quiet $RepoUrl $Src

    $WorkflowVersion = if (Test-Path (Join-Path $Src "VERSION")) { (Get-Content (Join-Path $Src "VERSION") -Raw).Trim() } else { "unknown" }
    $WorkflowCommit = git -C $Src rev-parse HEAD
    Write-Host "Workflow version $WorkflowVersion (commit $WorkflowCommit)"

    function Sync-Dir($RelPath) {
        $destPath = Join-Path $Target $RelPath
        $srcPath = Join-Path $Src $RelPath
        if (Test-Path $destPath) { Remove-Item -Recurse -Force $destPath }
        New-Item -ItemType Directory -Force -Path (Split-Path $destPath -Parent) | Out-Null
        Copy-Item -Recurse -Force $srcPath $destPath
    }

    function Keep-IfPresent($RelPath) {
        $destPath = Join-Path $Target $RelPath
        $srcPath = Join-Path $Src $RelPath
        if (Test-Path $destPath) {
            Write-Host "  keeping existing $RelPath"
        } else {
            New-Item -ItemType Directory -Force -Path (Split-Path $destPath -Parent) | Out-Null
            Copy-Item -Recurse -Force $srcPath $destPath
        }
    }

    Write-Host "Syncing workflow mechanism ..."
    Sync-Dir ".github\agents"
    Sync-Dir ".github\instructions"
    Sync-Dir ".github\skills"
    Sync-Dir ".github\prompts"
    Sync-Dir ".github\log-analyser\scripts"
    Sync-Dir ".github\mcp"
    New-Item -ItemType Directory -Force -Path (Join-Path $Target ".github\hooks\scripts") | Out-Null
    Copy-Item -Force (Join-Path $Src ".github\hooks\guards.json") (Join-Path $Target ".github\hooks\guards.json")
    Copy-Item -Force (Join-Path $Src ".github\hooks\hook-protocol.md") (Join-Path $Target ".github\hooks\hook-protocol.md")
    Copy-Item -Recurse -Force (Join-Path $Src ".github\hooks\scripts\*") (Join-Path $Target ".github\hooks\scripts")
    New-Item -ItemType Directory -Force -Path (Join-Path $Target "specs\.templates") | Out-Null
    Copy-Item -Recurse -Force (Join-Path $Src "specs\.templates\*") (Join-Path $Target "specs\.templates")
    New-Item -ItemType Directory -Force -Path (Join-Path $Target "docs") | Out-Null
    Copy-Item -Force (Join-Path $Src "docs\workflow-design.md") (Join-Path $Target "docs\workflow-design.md")
    Copy-Item -Force (Join-Path $Src "docs\field-sources.md") (Join-Path $Target "docs\field-sources.md")

    Write-Host "Preserving project data (only added if missing) ..."
    Keep-IfPresent ".github\copilot-instructions.md"
    Keep-IfPresent ".github\hooks\sensitive-paths.txt"
    Keep-IfPresent ".github\log-analyser\log-signatures.md"
    Keep-IfPresent ".mcp.json"
    Keep-IfPresent "project-context.md"
    Keep-IfPresent "architecture.md"

    $gitignore = Join-Path $Target ".gitignore"
    if (Test-Path $gitignore) {
        $lines = Get-Content $gitignore
        if (-not ($lines -contains ".logs/")) { Add-Content $gitignore ".logs/" }
    } else {
        Set-Content $gitignore ".logs/"
    }

    $syncedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $syncRecord = @"
# Workflow sync record

Do not edit by hand — every run of install.sh/install.ps1 overwrites this file.

- Source: $RepoUrl@$Branch
- Version: $WorkflowVersion
- Commit: $WorkflowCommit
- Synced at: $syncedAt

See this repo's CHANGELOG.md for what changed since a prior sync.
"@
    Set-Content (Join-Path $Target ".github\workflow-sync.md") $syncRecord

    Write-Host ""
    Write-Host "Done. Review with 'git status' / 'git diff' in $Target, then commit."
    $ci = Join-Path $Target ".github\copilot-instructions.md"
    if (-not (Test-Path $ci) -or (Select-String -Path $ci -Pattern "FILL IN" -Quiet)) {
        Write-Host "Next: fill in copilot-instructions.md's settings block, and draft project-context.md/architecture.md (see docs/field-sources.md)."
    }
} finally {
    Remove-Item -Recurse -Force $Tmp -ErrorAction SilentlyContinue
}
