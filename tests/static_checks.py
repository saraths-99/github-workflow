#!/usr/bin/env python3
"""Static checks for this repo's Copilot workflow files.

Validates the checked-in .github/ structure directly (there is no generator step anymore — see
docs/workflow-design.md). Two checks from the workflow's own quality list aren't covered here,
because they only make sense against real app code:
  - "every class, function and module named in a file exists in the code"
  - "project-context.md / architecture.md are byte-for-byte unchanged across a review"
Both are covered by written rules (each agent's own blueprint says never to touch those two docs)
rather than by this script.

Usage:
    python3 tests/static_checks.py
Exits 0 if every check passes, 1 otherwise, printing a pass/fail line per check.
"""
import json
import re
import sys
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


@check("agents follow Copilot frontmatter and have a body under 30,000 characters")
def _agents_check():
    agents_dir = ROOT / ".github/agents"
    files = sorted(agents_dir.glob("*.agent.md"))
    if not files:
        return False, "no agents found"
    mcp_config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server_names = set(mcp_config.get("mcpServers", {}))
    built_in_tools = {"read", "edit", "search", "execute", "agent", "web", "todo"}
    problems = []
    for f in files:
        fields, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fields.get("description"):
            problems.append(f"{f.name}: missing description")
        elif len(body) >= 30_000:
            problems.append(f"{f.name}: body is {len(body)} chars (>= 30,000)")
        if fields.get("target") != "github-copilot":
            problems.append(f"{f.name}: target must be github-copilot")
        if fields.get("user-invocable") not in ("false", "true"):
            problems.append(f"{f.name}: user-invocable must be explicitly true or false")
        if "mcp" in fields:
            problems.append(f"{f.name}: use MCP namespaces in tools, not mcp frontmatter")
        name = fields.get("name")
        stem = f.name[: -len(".agent.md")]
        if name != stem:
            problems.append(f"{f.name}: name '{name}' != filename '{stem}'")
        if name and not NAME_RE.match(name):
            problems.append(f"{f.name}: name '{name}' fails naming rule (lowercase-kebab)")
        tools = re.findall(r"['\"]([^'\"]+)['\"]", fields.get("tools", ""))
        if not tools:
            problems.append(f"{f.name}: tools must be a non-empty quoted list")
        for tool in tools:
            if tool in built_in_tools:
                continue
            if tool.endswith("/*") and tool[:-2] in server_names:
                continue
            problems.append(f"{f.name}: unsupported or unconfigured tool '{tool}'")
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
    inst_dir = ROOT / ".github/instructions"
    files = sorted(inst_dir.glob("*.instructions.md"))
    if not files:
        return False, "no instruction files found"
    problems = []
    for f in files:
        fields, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        if not fields.get("applyTo"):
            problems.append(f"{f.name}: missing applyTo")
    return (not problems), ("; ".join(problems) if problems else f"{len(files)} instruction files ok")


@check("hooks have version: 1 and real event names")
def _hooks_check():
    guards_path = ROOT / ".github/hooks/guards.json"
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


@check("the tasks spec template exists")
def _spec_templates_check():
    tmpl_dir = ROOT / "specs/.templates"
    required = ["tasks-template.md"]
    missing = [name for name in required if not (tmpl_dir / name).exists()]
    return (not missing), (f"missing: {missing}" if missing else "present")


@check("MCP configuration files are valid and contain no token")
def _mcp_files_check():
    files = [
        ROOT / ".mcp.json",
        ROOT / ".github/mcp/jetbrains-mcp.example.json",
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

    return (not problems), ("; ".join(problems) if problems else "all files valid, no tokens")


@check("sensitive-paths.txt exists and lists the sensitive paths")
def _sensitive_paths_check():
    f = ROOT / ".github/hooks/sensitive-paths.txt"
    if not f.exists():
        return False, "file not found"
    lines = [l.strip() for l in f.read_text(encoding="utf-8").splitlines()]
    entries = [l for l in lines if l and not l.startswith("#")]
    return (len(entries) >= 5), f"{len(entries)} entries"


@check("no leftover generator/bootstrap references")
def _no_generator_leftovers_check():
    needles = ["setup-workflow", "setup-agents", "setup-instructions", "setup-hooks", "setup-mcp",
               "setup-skills", "setup-ticket-flow", "setup-context-docs", "generated-by", "bootstrap.sh"]
    problems = []
    for base in (".github", "specs", "project-context.md", "architecture.md"):
        p = ROOT / base
        paths = [p] if p.is_file() else (list(p.rglob("*")) if p.is_dir() else [])
        for f in paths:
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in needles:
                if needle in text:
                    problems.append(f"{f.relative_to(ROOT)}: contains '{needle}'")
    return (not problems), ("; ".join(problems) if problems else "clean")


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
