#!/usr/bin/env python3
"""Points every agent's and prompt's `model:` line at one provider's models.

  set-models.py <claude|gpt> <app repo>

Each `model:` line in .github/agents/*.agent.md and .github/prompts/*.prompt.md holds one tier's
list from models.json (deep, standard or fast). This finds the tier by matching the line against
every provider's lists, and replaces it with the chosen provider's list for that tier. A line that
matches no list is left alone and reported. Standard library only.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_LINE = re.compile(r"^model: (\[.*\])\s*$", re.M)


def render(names):
    return "[" + ", ".join(f"'{n} (copilot)'" for n in names) + "]"


def load():
    data = json.loads((HERE / "models.json").read_text(encoding="utf-8"))
    return data["providers"]


def set_models(provider, target, providers=None):
    """Rewrites the files under target; returns (files changed, unmatched lines)."""
    providers = providers or load()
    if provider not in providers:
        raise SystemExit(f"unknown provider {provider!r}; choose one of: {', '.join(providers)}")
    by_text = {}
    for lists in providers.values():
        for tier, names in lists.items():
            by_text[render(names)] = tier
    changed, unmatched = 0, []
    target = Path(target)
    files = sorted(target.glob(".github/agents/*.agent.md")) + sorted(target.glob(".github/prompts/*.prompt.md"))
    for f in files:
        text = f.read_text(encoding="utf-8")

        def swap(m):
            tier = by_text.get(m.group(1))
            if tier is None:
                unmatched.append(f"{f.name}: {m.group(1)}")
                return m.group(0)
            return "model: " + render(providers[provider][tier])

        new = MODEL_LINE.sub(swap, text)
        if new != text:
            f.write_text(new, encoding="utf-8")
            changed += 1
    return changed, unmatched


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__.strip())
    changed, unmatched = set_models(argv[1], argv[2])
    print(f"  models: {argv[1]} ({changed} files changed)")
    for u in unmatched:
        print(f"  warning: left alone, matches no tier: {u}")


if __name__ == "__main__":
    main(sys.argv)
