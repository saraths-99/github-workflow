#!/usr/bin/env bash
# Copies the setup-* skills and the /setup-workflow prompt from this builder repo
# into an app repo's .github/, so its developer can run /setup-workflow in Android
# Studio. Writes nothing under ~/.copilot/, and never touches the app repo's
# .agents/, .claude/, .android-studio/ or AGENTS.md.
set -euo pipefail

usage() {
  echo "Usage: $0 <path-to-app-repo>" >&2
  echo "  <path-to-app-repo>  the Android Studio project root to bootstrap" >&2
  exit 1
}

[ "$#" -eq 1 ] || usage

BUILDER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_REPO="$(cd "$1" 2>/dev/null && pwd)" || { echo "error: '$1' is not a directory" >&2; exit 1; }

SRC_SKILLS="$BUILDER_DIR/.github/skills"
SRC_PROMPT="$BUILDER_DIR/.github/prompts/setup-workflow.prompt.md"
DST_SKILLS="$APP_REPO/.github/skills"
DST_PROMPTS="$APP_REPO/.github/prompts"

mkdir -p "$DST_SKILLS" "$DST_PROMPTS"

copied_any=0
for skill_dir in "$SRC_SKILLS"/setup-*/; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  rm -rf "$DST_SKILLS/$name"
  cp -R "$skill_dir" "$DST_SKILLS/$name"
  echo "copied skill: $name"
  copied_any=1
done

if [ "$copied_any" -eq 0 ]; then
  echo "warning: no setup-* skills found under $SRC_SKILLS (builder repo not yet past phase 1)" >&2
fi

if [ -f "$SRC_PROMPT" ]; then
  cp "$SRC_PROMPT" "$DST_PROMPTS/setup-workflow.prompt.md"
  echo "copied prompt: setup-workflow.prompt.md"
else
  echo "warning: $SRC_PROMPT not found yet (builder repo not yet past phase 2)" >&2
fi

echo "done. Open '$APP_REPO' in Android Studio and run /setup-workflow in Copilot chat."
