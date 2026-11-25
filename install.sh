#!/usr/bin/env bash
# Installs/updates the Agentic AI-SDLC workflow from this repo into an app repo.
#
# Usage, from inside the app repo (the common case):
#   curl -fsSL https://raw.githubusercontent.com/saraths-99/github-workflow/develop/install.sh | bash
#
# Or, with a local checkout of this repo:
#   /path/to/github-workflow/install.sh [--provider claude|gpt] [target-repo-path]
#   (the target defaults to the current directory)
#
# --provider chooses which models the agents run on: Claude's or GPT's (models.json lists them).
# Without it, the last install's choice is reused; a first install asks, or uses claude where there
# is no terminal to ask on. With curl: `... | bash -s -- --provider gpt`.
#
# Can't run this script at all (no shell, or this repo is only a downloaded .zip)? See README.md
# §2a for exactly which files to copy by hand instead -- don't just copy the whole extracted
# folder into the app repo.
#
# What it does:
#   - Downloads this repo (a shallow clone of REPO_URL@BRANCH) into a temp dir.
#   - Overwrites the *mechanism* files (agents, instructions, skills, prompts,
#     log-analyser scripts, token-tracker) with the latest from this repo -- these
#     are maintained here, not hand-edited per app repo, so a later re-run is how you pick up a fix.
#   - Never overwrites the *project data* files if they already exist: copilot-instructions.md
#     (your settings block, module map, key rules),
#     project-context.md, architecture.md,
#     .mcp.json (which may contain other project servers), and anything under specs/ (ticket data).
#   - Installs only what the workflow uses in the app repo. Reference material -- the JetBrains MCP
#     snippet, docs/field-sources.md -- stays in this repo, and copies
#     left by an older install are removed.
#   - Leaves everything git-tracked in the target repo, so `git status`/`git diff` shows exactly
#     what changed and the run is trivially reversible.
#   - Points every agent's and prompt's `model:` line at the chosen provider (set-models.py).
#   - Writes .github/workflow-sync.md every run, recording the synced version, commit SHA,
#     provider and timestamp -- check this file to see what an app repo is currently running, and this repo's
#     CHANGELOG.md to see what changed since.
set -euo pipefail

REPO_URL="https://github.com/saraths-99/github-workflow.git"
BRANCH="develop"

PROVIDER="${WORKFLOW_PROVIDER:-}"
TARGET_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --provider)
      [ $# -ge 2 ] || { echo "error: --provider needs claude or gpt" >&2; exit 1; }
      PROVIDER="$2"; shift 2 ;;
    --provider=*) PROVIDER="${1#*=}"; shift ;;
    *) TARGET_ARG="$1"; shift ;;
  esac
done
TARGET="${TARGET_ARG:-$(pwd)}"
TARGET="$(cd "$TARGET" && pwd)"

if ! git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: $TARGET is not a git repo. Run this from inside the app repo you want to install into." >&2
  exit 1
fi

valid_provider() { [ "$1" = "claude" ] || [ "$1" = "gpt" ]; }

if [ -n "$PROVIDER" ] && ! valid_provider "$PROVIDER"; then
  echo "error: unknown provider '$PROVIDER'; choose claude or gpt." >&2
  exit 1
fi
if [ -z "$PROVIDER" ] && [ -f "$TARGET/.github/workflow-sync.md" ]; then
  PROVIDER="$(sed -n 's/^- Provider: //p' "$TARGET/.github/workflow-sync.md" | head -n 1)"
  if valid_provider "$PROVIDER"; then
    echo "Using model provider '$PROVIDER' from the last install (pass --provider claude|gpt to change it)."
  else
    PROVIDER=""
  fi
fi
if [ -z "$PROVIDER" ]; then
  if (: </dev/tty) 2>/dev/null; then
    printf 'Which models should the agents run on?\n  1) Claude\n  2) GPT\nChoose [1]: ' >/dev/tty
    read -r answer </dev/tty || answer=""
    case "$answer" in 2|gpt|GPT|Gpt) PROVIDER="gpt" ;; *) PROVIDER="claude" ;; esac
  else
    PROVIDER="claude"
    echo "No terminal to ask on; using claude. Pass --provider gpt to use GPT models."
  fi
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
sync_dir .github/token-tracker
# The files here carry Claude's models; switch them to GPT's when that was chosen.
if [ "$PROVIDER" != "claude" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "error: python3 is needed to switch the agents to $PROVIDER models." >&2; exit 1; }
  python3 "$SRC/set-models.py" "$PROVIDER" "$TARGET"
fi
echo "Model provider: $PROVIDER"
mkdir -p "$TARGET/specs/.templates"
cp -R "$SRC/specs/.templates/." "$TARGET/specs/.templates/"
cp "$SRC/.github/workflow-guide.md" "$TARGET/.github/workflow-guide.md"
mkdir -p "$TARGET/docs"
cp "$SRC/docs/workflow-design.md" "$TARGET/docs/workflow-design.md"

# Reference material an older install copied in; it stays in this repo now.
rm -rf "$TARGET/.github/mcp"
rm -f "$TARGET/docs/field-sources.md"
# The workflow no longer ships guard hooks; remove the files an older install copied in. A
# hooks/sensitive-paths.txt is left alone (it is the app repo's own data) and can be deleted by hand.
rm -f "$TARGET/.github/hooks/guards.json" "$TARGET/.github/hooks/hook-protocol.md"
for guard in format-kotlin block-force-push protect-secrets guard-context-docs; do
  rm -f "$TARGET/.github/hooks/scripts/$guard.sh" "$TARGET/.github/hooks/scripts/$guard.ps1"
done
rm -f "$TARGET/.github/hooks/scripts/guards.py"
rmdir "$TARGET/.github/hooks/scripts" "$TARGET/.github/hooks" 2>/dev/null || true

echo "Preserving project data (only added if missing) ..."
keep_if_present .github/copilot-instructions.md
keep_if_present .mcp.json
keep_if_present project-context.md
keep_if_present architecture.md

# Token tracking in VS Code needs one Copilot setting; add it only to a repo with no settings file
# of its own, and never edit an existing one.
if [ ! -e "$TARGET/.vscode/settings.json" ]; then
  mkdir -p "$TARGET/.vscode"
  cp "$SRC/.github/token-tracker/vscode-settings.json" "$TARGET/.vscode/settings.json"
elif ! grep -q 'github.copilot.chat.otel.dbSpanExporter.enabled' "$TARGET/.vscode/settings.json"; then
  echo "  note: for token tracking in VS Code, add \"github.copilot.chat.otel.dbSpanExporter.enabled\": true to .vscode/settings.json"
fi

touch "$TARGET/.gitignore"
for entry in '.logs/' '.github/'; do
  grep -qxF "$entry" "$TARGET/.gitignore" || echo "$entry" >> "$TARGET/.gitignore"
done

cat > "$TARGET/.github/workflow-sync.md" <<EOF
# Workflow sync record

Do not edit by hand — every run of install.sh overwrites this file.

- Source: $REPO_URL@$BRANCH
- Version: $WORKFLOW_VERSION
- Commit: $WORKFLOW_COMMIT
- Provider: $PROVIDER
- Synced at: $(date -u +%Y-%m-%dT%H:%M:%SZ)

See this repo's CHANGELOG.md for what changed since a prior sync.
EOF

echo
echo "Done. Review with 'git status' / 'git diff' in $TARGET, then commit."
if [ ! -f "$TARGET/.github/copilot-instructions.md" ] || grep -q 'FILL IN' "$TARGET/.github/copilot-instructions.md" 2>/dev/null; then
  echo "Next: fill in copilot-instructions.md's settings block, and draft project-context.md/architecture.md (see https://github.com/saraths-99/github-workflow/blob/develop/docs/field-sources.md)."
fi
