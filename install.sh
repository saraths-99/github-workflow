#!/usr/bin/env bash
# Installs/updates the Agentic AI-SDLC workflow from this repo into an app repo.
#
# Usage, from inside the app repo (the common case):
#   curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash
#
# Or, with a local checkout of this repo:
#   /path/to/github-workflow/install.sh [target-repo-path]   # defaults to the current directory
#
# Can't run this script at all (no shell, or this repo is only a downloaded .zip)? See README.md
# §2a for exactly which files to copy by hand instead -- don't just copy the whole extracted
# folder into the app repo.
#
# What it does:
#   - Downloads this repo (a shallow clone of REPO_URL@BRANCH) into a temp dir.
#   - Overwrites the *mechanism* files (agents, instructions, skills, prompts, hooks scripts,
#     guards.json, mcp server list, log-analyser scripts) with the latest from this repo -- these
#     are maintained here, not hand-edited per app repo, so a later re-run is how you pick up a fix.
#   - Never overwrites the *project data* files if they already exist: copilot-instructions.md
#     (your settings block, module map, key rules), hooks/sensitive-paths.txt and
#     log-analyser/log-signatures.md (both grow over time), project-context.md, architecture.md,
#     .mcp.json (which may contain other project servers), and anything under specs/ (ticket data).
#   - Leaves everything git-tracked in the target repo, so `git status`/`git diff` shows exactly
#     what changed and the run is trivially reversible.
#   - Writes .github/workflow-sync.md every run, recording the synced version, commit SHA, and
#     timestamp -- check this file to see what an app repo is currently running, and this repo's
#     CHANGELOG.md to see what changed since.
set -euo pipefail

REPO_URL="https://github.com/saraths-99/github-workflow.git"
BRANCH="develop"

TARGET="${1:-$(pwd)}"
TARGET="$(cd "$TARGET" && pwd)"

if ! git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: $TARGET is not a git repo. Run this from inside the app repo you want to install into." >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Downloading $REPO_URL@$BRANCH ..."
git clone --depth 1 --branch "$BRANCH" --quiet "$REPO_URL" "$TMP/src"
SRC="$TMP/src"

WORKFLOW_VERSION="$(cat "$SRC/VERSION" 2>/dev/null || echo "unknown")"
WORKFLOW_COMMIT="$(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo "unknown")"
echo "Workflow version $WORKFLOW_VERSION (commit $WORKFLOW_COMMIT)"

sync_dir() {
  # Replaces $TARGET/$1 wholesale with $SRC/$1.
  rm -rf "${TARGET:?}/$1"
  mkdir -p "$(dirname "$TARGET/$1")"
  cp -R "$SRC/$1" "$TARGET/$1"
}

keep_if_present() {
  # Copies $SRC/$1 to $TARGET/$1 only if the target doesn't already have it.
  if [ -e "$TARGET/$1" ]; then
    echo "  keeping existing $1"
  else
    mkdir -p "$(dirname "$TARGET/$1")"
    cp -R "$SRC/$1" "$TARGET/$1"
  fi
}

echo "Syncing workflow mechanism ..."
sync_dir .github/agents
sync_dir .github/instructions
sync_dir .github/skills
sync_dir .github/prompts
sync_dir .github/log-analyser/scripts
sync_dir .github/mcp
mkdir -p "$TARGET/.github/hooks/scripts"
cp "$SRC/.github/hooks/guards.json" "$TARGET/.github/hooks/guards.json"
cp "$SRC/.github/hooks/hook-protocol.md" "$TARGET/.github/hooks/hook-protocol.md"
cp -R "$SRC/.github/hooks/scripts/." "$TARGET/.github/hooks/scripts/"
mkdir -p "$TARGET/specs/.templates"
cp -R "$SRC/specs/.templates/." "$TARGET/specs/.templates/"
mkdir -p "$TARGET/docs"
cp "$SRC/docs/workflow-design.md" "$TARGET/docs/workflow-design.md"
cp "$SRC/docs/field-sources.md" "$TARGET/docs/field-sources.md"

echo "Preserving project data (only added if missing) ..."
keep_if_present .github/copilot-instructions.md
keep_if_present .github/hooks/sensitive-paths.txt
keep_if_present .github/log-analyser/log-signatures.md
keep_if_present .mcp.json
keep_if_present project-context.md
keep_if_present architecture.md

if [ -f "$TARGET/.gitignore" ]; then
  grep -qxF '.logs/' "$TARGET/.gitignore" || echo '.logs/' >> "$TARGET/.gitignore"
else
  echo '.logs/' > "$TARGET/.gitignore"
fi

cat > "$TARGET/.github/workflow-sync.md" <<EOF
# Workflow sync record

Do not edit by hand — every run of install.sh/install.ps1 overwrites this file.

- Source: $REPO_URL@$BRANCH
- Version: $WORKFLOW_VERSION
- Commit: $WORKFLOW_COMMIT
- Synced at: $(date -u +%Y-%m-%dT%H:%M:%SZ)

See this repo's CHANGELOG.md for what changed since a prior sync.
EOF

echo
echo "Done. Review with 'git status' / 'git diff' in $TARGET, then commit."
if [ ! -f "$TARGET/.github/copilot-instructions.md" ] || grep -q 'FILL IN' "$TARGET/.github/copilot-instructions.md" 2>/dev/null; then
  echo "Next: fill in copilot-instructions.md's settings block, and draft project-context.md/architecture.md (see docs/field-sources.md)."
fi
