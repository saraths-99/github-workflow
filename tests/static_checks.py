#!/usr/bin/env python3
"""Static checks for the builder repo's generated-file blueprints.

Implements the "Static checks" row from the workflow's own section 7 (Quality and acceptance),
run here against this builder repo's setup-*/assets/ blueprints directly -- there is no fixture
app repo yet (see the top-level README: phase 9's fixtures and lifecycle evals are still open),
so this validates the files setup-workflow *would* generate, not a generated repo.

Two items from that list aren't checked here, because they only make sense once setup-workflow has
actually run against a real app repo with real code and a pre-existing context doc:
  - "every class, function and module named in a file exists in the code"
  - "existing context docs are byte-for-byte unchanged"
Both are covered by written rules (setup-context-docs/SKILL.md's "never touch an existing doc";
architect's/developer's blueprints grounding claims in the real code) and are meant to be verified
by the lifecycle evals, not by this script.

Usage:
    python3 tests/static_checks.py
Exits 0 if every check passes, 1 otherwise, printing a pass/fail line per check.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

results = []


def check(name):
    def decorator(fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - surface any failure as a failed check
            ok, detail = False, f"raised {exc!r}"
        results.append((name, ok, detail))
        return fn
    return decorator


def parse_frontmatter(text):
    """Minimal frontmatter parser: flat keys, with '>' / '|' block scalars folded or joined."""
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:])

    fields = {}
    key = None
    mode = None  # ">" or "|" or None
    buf = []

    def flush():
        if key is None:
            return
        if mode == ">":
            fields[key] = " ".join(buf).strip()
        elif mode == "|":
            fields[key] = "\n".join(buf)
        # else: literal scalar already stored directly in fields[key]

    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith(" "):
            flush()
            key, value = m.group(1), m.group(2).strip()
            if value in (">", "|"):
                mode, buf = value, []
            else:
                mode = None
                fields[key] = value.strip('"').strip("'")
        elif mode in (">", "|"):
            buf.append(line.strip() if mode == ">" else (line[2:] if line.startswith("  ") else line))
    flush()
    return fields, body


@check("agents have a description and a body under 30,000 characters")
def _agents_check():
    agents_dir = ROOT / ".github/skills/setup-agents/assets/agents"
    files = sorted(agents_dir.glob("*.agent.md"))
    if not files:
        return False, "no agent blueprints found"
    problems = []
    for f in files:
        fields, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fields.get("description"):
            problems.append(f"{f.name}: missing description")
        elif len(body) >= 30_000:
            problems.append(f"{f.name}: body is {len(body)} chars (>= 30,000)")
    return (not problems), ("; ".join(problems) if problems else f"{len(files)} agents ok")


@check("every skill's name matches its folder and follows the naming rules")
def _skill_naming_check():
    skill_mds = sorted(ROOT.glob(".github/skills/**/SKILL.md"))
    if not skill_mds:
        return False, "no SKILL.md files found"
    problems = []
    for f in skill_mds:
        folder = f.parent.name
        fields, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        name = fields.get("name")
        if not name:
            problems.append(f"{f}: missing name in frontmatter")
            continue
        if name != folder:
            problems.append(f"{f}: name '{name}' != folder '{folder}'")
        if not NAME_RE.match(name):
            problems.append(f"{f}: name '{name}' fails naming rule (lowercase-kebab)")
    return (not problems), ("; ".join(problems) if problems else f"{len(skill_mds)} skills ok")


@check("instructions have an applyTo")
def _instructions_check():
    inst_dir = ROOT / ".github/skills/setup-instructions/assets"
    files = sorted(inst_dir.glob("*.instructions.md"))
    if not files:
        return False, "no instruction blueprints found"
    problems = []
    for f in files:
        fields, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fields.get("applyTo"):
            problems.append(f"{f.name}: missing applyTo")
    return (not problems), ("; ".join(problems) if problems else f"{len(files)} instruction files ok")


@check("hooks have version: 1 and real event names")
def _hooks_check():
    guards_path = ROOT / ".github/skills/setup-hooks/assets/guards.json"
    if not guards_path.exists():
        return False, "guards.json not found"
    data = json.loads(guards_path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        return False, f"version is {data.get('version')!r}, expected 1"
    real_events = {"preToolUse", "postToolUse"}
    problems = []
    for hook in data.get("hooks", []):
        if hook.get("event") not in real_events:
            problems.append(f"{hook.get('name')}: bad event {hook.get('event')!r}")
    return (not problems), ("; ".join(problems) if problems else f"{len(data.get('hooks', []))} hooks ok")


@check("spec templates exist for all three files")
def _spec_templates_check():
    tmpl_dir = ROOT / ".github/skills/setup-ticket-flow/assets/spec-templates"
    required = ["requirements-template.md", "design-template.md", "tasks-template.md"]
    missing = [name for name in required if not (tmpl_dir / name).exists()]
    return (not missing), (f"missing: {missing}" if missing else "all 3 present")


@check("both MCP files are valid and contain no token")
def _mcp_files_check():
    files = [
        ROOT / ".github/skills/setup-mcp/assets/mcp.json",
        ROOT / ".github/skills/setup-mcp/assets/mcp/jetbrains-mcp.example.json",
    ]
    problems = []
    secret_key_re = re.compile(r"(?i)(token|secret|api[_-]?key)")

    def walk(obj, path, probs):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and secret_key_re.search(k):
                    if v.strip() and "<" not in v:
                        probs.append(f"field '{path}{k}' looks like a real secret")
                walk(v, f"{path}{k}.", probs)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, path, probs)

    for f in files:
        if not f.exists():
            problems.append(f"{f}: missing")
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"{f}: invalid JSON ({exc})")
            continue
        file_problems = []
        walk(data, "", file_problems)
        problems.extend(f"{f}: {p}" for p in file_problems)

    return (not problems), ("; ".join(problems) if problems else "both files valid, no tokens")


@check("sensitive-paths.txt exists and lists the sensitive paths")
def _sensitive_paths_check():
    f = ROOT / ".github/skills/setup-hooks/assets/sensitive-paths.txt"
    if not f.exists():
        return False, "file not found"
    lines = [l.strip() for l in f.read_text(encoding="utf-8").splitlines()]
    entries = [l for l in lines if l and not l.startswith("#")]
    return (len(entries) >= 5), f"{len(entries)} entries"


@check("bootstrap copies only the setup-* skills and the /setup-workflow prompt, writes nothing under ~/.copilot/")
def _bootstrap_scope_check():
    with tempfile.TemporaryDirectory() as tmp:
        app_repo = Path(tmp) / "app-repo"
        fake_home = Path(tmp) / "fake-home"
        app_repo.mkdir()
        fake_home.mkdir()

        env = dict(os.environ)
        env["HOME"] = str(fake_home)

        proc = subprocess.run(
            [str(ROOT / "bootstrap.sh"), str(app_repo)],
            env=env, capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return False, f"bootstrap.sh exited {proc.returncode}: {proc.stderr.strip()}"

        problems = []
        skills_dir = app_repo / ".github/skills"
        for entry in skills_dir.iterdir():
            if not entry.name.startswith("setup-"):
                problems.append(f"unexpected skill copied: {entry.name}")

        prompts_dir = app_repo / ".github/prompts"
        prompt_files = [p.name for p in prompts_dir.iterdir()] if prompts_dir.exists() else []
        if prompt_files != ["setup-workflow.prompt.md"]:
            problems.append(f"unexpected prompts copied: {prompt_files}")

        if (fake_home / ".copilot").exists():
            problems.append("wrote under ~/.copilot/")

        for forbidden in (".agents", ".claude", ".android-studio", "AGENTS.md"):
            if (app_repo / forbidden).exists():
                problems.append(f"wrote to forbidden path: {forbidden}")

        return (not problems), ("; ".join(problems) if problems else "bootstrap scope ok")


def main():
    width = max(len(name) for name, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name.ljust(width)}  {detail}")
        if not ok:
            failed += 1

    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
