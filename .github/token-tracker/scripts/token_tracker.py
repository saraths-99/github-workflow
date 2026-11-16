#!/usr/bin/env python3
"""Per-ticket Copilot token usage, read from Copilot's own local traces.

  token_tracker.py mark <ticket ID>     record that work on a ticket starts now
  token_tracker.py collect              copy new model calls from Copilot's traces into .logs/
  token_tracker.py report <ticket ID>   collect, then write that ticket's usage report

Sources: VS Code Copilot Chat's local trace database (agent-traces.db, enabled by the
`github.copilot.chat.otel.dbSpanExporter.enabled` setting) and the Copilot CLI's JSON-lines trace
file (written when the CLI is started through copilot-tracked.sh / copilot-tracked.ps1).
Standard library only.
"""
import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["ticketId", "agentName", "model", "inputTokens", "outputTokens", "timestamp"]
TICKET_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
GENERIC_AGENT_NAMES = {"", "GitHub Copilot Chat", "default"}
# Copilot deletes its own trace rows after 7 days, so `collect` keeps a durable copy here.
CALLS_FILE = "calls.jsonl"
MARKERS_FILE = "markers.jsonl"
CLI_TRACE_FILE = "copilot-cli-otel.jsonl"
# A marker counts for a chat if it was written while that chat was active, give or take this much.
SESSION_SLACK_MS = 10 * 60 * 1000

ATTR_MODE = "copilot_chat.mode_name"
ATTR_BRANCH = "copilot_chat.repo.head_branch_name"
ATTR_REMOTE = "copilot_chat.repo.remote_url"
ATTR_CHAT_SESSION = "copilot_chat.chat_session_id"


def repo_root():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def tracker_dir(root):
    d = root / ".logs" / "token-tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def remote_key(url):
    """Reduces any form of a git remote URL to host/path, so https and ssh forms compare equal."""
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^[a-z+]+://", "", u)
    u = re.sub(r"^[^@/]+@", "", u)
    u = u.replace(":", "/", 1) if re.match(r"^[^/]+:[^/0-9]", u) else u
    u = re.sub(r":\d+/", "/", u)
    return u.rstrip("/").removesuffix(".git")


def current_remote(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
        return remote_key(out.stdout)
    except (OSError, subprocess.CalledProcessError):
        pass
    try:
        out = subprocess.run(["git", "-C", str(root), "remote"], capture_output=True, text=True, check=True)
        first = out.stdout.split()
        if first:
            url = subprocess.run(["git", "-C", str(root), "remote", "get-url", first[0]], capture_output=True, text=True, check=True)
            return remote_key(url.stdout)
    except (OSError, subprocess.CalledProcessError):
        pass
    return ""


# ── Sources ──────────────────────────────────────────────────────────────────────────────────────


def vscode_db_paths():
    override = os.environ.get("TOKEN_TRACKER_VSCODE_DB")
    if override:
        return [Path(override)] if Path(override).is_file() else []
    home = Path.home()
    if sys.platform == "win32":
        bases = [Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))]
    elif sys.platform == "darwin":
        bases = [home / "Library" / "Application Support"]
    else:
        bases = [Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))]
    found = []
    for base in bases:
        for product in ("Code", "Code - Insiders", "VSCodium"):
            p = base / product / "User" / "globalStorage" / "github.copilot-chat" / "agent-traces.db"
            if p.is_file():
                found.append(p)
    fallback = Path(tempfile.gettempdir()) / "copilot-agent-traces.db"
    if fallback.is_file():
        found.append(fallback)
    return found


def read_vscode_db(path):
    """Reads a copy of the database, so the live one VS Code is writing to is never locked."""
    with tempfile.TemporaryDirectory() as tmp:
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(path) + suffix)
            if src.is_file():
                shutil.copy2(src, Path(tmp) / ("agent-traces.db" + suffix))
        conn = sqlite3.connect(Path(tmp) / "agent-traces.db")
        try:
            attrs = {}
            for span_id, key, value in conn.execute(
                "SELECT span_id, key, value FROM span_attributes WHERE key IN (?, ?, ?)",
                (ATTR_MODE, ATTR_BRANCH, ATTR_REMOTE),
            ):
                attrs.setdefault(span_id, {})[key] = value
            spans = []
            for row in conn.execute(
                "SELECT span_id, trace_id, parent_span_id, name, start_time_ms, operation_name, agent_name,"
                " conversation_id, chat_session_id, request_model, response_model, input_tokens, output_tokens"
                " FROM spans"
            ):
                (span_id, trace_id, parent, name, start, op, agent, conv, chat_session,
                 req_model, resp_model, inp, out) = row
                a = attrs.get(span_id, {})
                spans.append({
                    "id": span_id, "trace": trace_id, "parent": parent, "name": name or "",
                    "start_ms": int(start or 0), "op": op, "agent": agent, "mode": a.get(ATTR_MODE),
                    "conv": conv or chat_session, "branch": a.get(ATTR_BRANCH), "remote": a.get(ATTR_REMOTE),
                    "model": resp_model or req_model, "inp": inp, "out": out,
                })
            return spans
        finally:
            conn.close()


def _otlp_value(v):
    if not isinstance(v, dict):
        return v
    for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
        if k in v:
            return int(v[k]) if k == "intValue" else v[k]
    return None


def _attrs(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {a.get("key"): _otlp_value(a.get("value")) for a in raw if isinstance(a, dict)}
    return {}


def _to_ms(t):
    if isinstance(t, list) and len(t) == 2:
        return int(t[0]) * 1000 + int(t[1]) // 1_000_000
    if isinstance(t, str):
        if t.isdigit():
            t = int(t)
        else:
            try:
                return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp() * 1000)
            except ValueError:
                return 0
    if isinstance(t, (int, float)):
        if t > 1e17:
            return int(t // 1_000_000)
        if t > 1e14:
            return int(t // 1000)
        if t > 1e11:
            return int(t)
        return int(t * 1000)
    return 0


def _int_or_none(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _span_from(obj):
    if not isinstance(obj, dict) or "name" not in obj:
        return None
    ctx = obj.get("spanContext") or obj.get("_spanContext") or {}
    parent_ctx = obj.get("parentSpanContext") or {}
    span_id = obj.get("spanId") or ctx.get("spanId")
    if not span_id:
        return None
    a = _attrs(obj.get("attributes"))
    start = obj.get("startTimeUnixNano") or obj.get("startTime") or obj.get("start_time")
    return {
        "id": span_id,
        "trace": obj.get("traceId") or ctx.get("traceId"),
        "parent": obj.get("parentSpanId") or parent_ctx.get("spanId") or None,
        "name": obj.get("name") or "",
        "start_ms": _to_ms(start),
        "op": a.get("gen_ai.operation.name"),
        "agent": a.get("gen_ai.agent.name"),
        "mode": a.get(ATTR_MODE),
        "conv": a.get("gen_ai.conversation.id") or a.get(ATTR_CHAT_SESSION),
        "branch": a.get(ATTR_BRANCH),
        "remote": a.get(ATTR_REMOTE),
        "model": a.get("gen_ai.response.model") or a.get("gen_ai.request.model"),
        "inp": _int_or_none(a.get("gen_ai.usage.input_tokens")),
        "out": _int_or_none(a.get("gen_ai.usage.output_tokens")),
    }


def read_trace_jsonl(path):
    """Returns (spans, lines that held no readable span)."""
    spans, unreadable = [], 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                unreadable += 1
                continue
            found = []
            if isinstance(obj, dict) and "resourceSpans" in obj:
                for rs in obj.get("resourceSpans") or []:
                    for ss in rs.get("scopeSpans") or rs.get("instrumentationLibrarySpans") or []:
                        found.extend(s for s in map(_span_from, ss.get("spans") or []) if s)
            else:
                s = _span_from(obj)
                if s:
                    found.append(s)
            if found:
                spans.extend(found)
            elif obj == {}:
                unreadable += 1
    return spans, unreadable


# ── Spans → model calls ──────────────────────────────────────────────────────────────────────────


def _is_agent(s):
    return s["op"] == "invoke_agent" or (s["op"] is None and s["name"].startswith("invoke_agent"))


def _is_chat(s):
    return s["op"] == "chat" or (s["op"] is None and s["name"].startswith("chat"))


def _agent_label(s):
    """An agent picked from the picker is recorded as "GitHub Copilot Chat" with its own name in the mode attribute."""
    name = s.get("agent") or ""
    if name in GENERIC_AGENT_NAMES and s.get("mode"):
        return s["mode"]
    return name or s.get("mode") or "unknown"


def spans_to_calls(spans, source):
    by_id = {s["id"]: s for s in spans}

    def ancestors(s):
        seen = set()
        p = by_id.get(s["parent"]) if s["parent"] else None
        while p and p["id"] not in seen:
            seen.add(p["id"])
            yield p
            p = by_id.get(p["parent"]) if p["parent"] else None

    def describe(s, chain):
        agents = [a for a in chain if _is_agent(a)]
        own = s if _is_agent(s) else (agents[0] if agents else None)
        top = agents[-1] if agents else own
        branch = next((a["branch"] for a in ([own] if own else []) + agents if a and a.get("branch")), None)
        remote = next((a["remote"] for a in ([own] if own else []) + agents if a and a.get("remote")), None)
        return {
            "id": f"{source}:{s['id']}",
            "source": source,
            "session": (top or s).get("conv") or s.get("conv") or s.get("trace") or s["id"],
            "branch": branch,
            "remote": remote_key(remote),
            "agentName": _agent_label(own) if own else (s.get("agent") or "unknown"),
            "model": s.get("model") or (own or {}).get("model") or "unknown",
            "inputTokens": int(s.get("inp") or 0),
            "outputTokens": int(s.get("out") or 0),
            "timestamp_ms": s["start_ms"],
        }

    calls, has_chat_below = [], set()
    for s in spans:
        if _is_chat(s) and (s["inp"] is not None or s["out"] is not None):
            chain = list(ancestors(s))
            has_chat_below.update(a["id"] for a in chain)
            calls.append(describe(s, chain))
    # An agent with token totals but no per-call spans under it (seen in some CLI traces) counts once.
    for s in spans:
        if _is_agent(s) and s["id"] not in has_chat_below and (s["inp"] is not None or s["out"] is not None):
            calls.append(describe(s, list(ancestors(s))))
    return calls


# ── Store ────────────────────────────────────────────────────────────────────────────────────────


def load_jsonl(path):
    if not path.is_file():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def write_jsonl(path, rows):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)


def collect(root, quiet=False):
    tdir = tracker_dir(root)
    this_repo = current_remote(root)
    calls_path = tdir / CALLS_FILE
    stored = {c["id"]: c for c in load_jsonl(calls_path)}
    before = len(stored)
    notes = []

    sources = [(p, "vscode") for p in vscode_db_paths()]
    cli_paths = [tdir / CLI_TRACE_FILE]
    if os.environ.get("TOKEN_TRACKER_CLI_TRACE"):
        cli_paths.append(Path(os.environ["TOKEN_TRACKER_CLI_TRACE"]))
    sources += [(p, "cli") for p in cli_paths if p.is_file()]

    for path, kind in sources:
        try:
            if kind == "vscode":
                spans = read_vscode_db(path)
            else:
                spans, unreadable = read_trace_jsonl(path)
                if unreadable and not spans:
                    notes.append(f"{path}: {unreadable} lines but no readable trace records")
        except (sqlite3.Error, OSError) as e:
            notes.append(f"{path}: could not read ({e})")
            continue
        calls = spans_to_calls(spans, kind)
        sessions_elsewhere = {c["session"] for c in calls if this_repo and c["remote"] and c["remote"] != this_repo}
        sessions_here = {c["session"] for c in calls if this_repo and c["remote"] == this_repo}
        for c in calls:
            if c["session"] in sessions_elsewhere and c["session"] not in sessions_here:
                continue
            stored[c["id"]] = c

    rows = sorted(stored.values(), key=lambda c: (c["timestamp_ms"], c["id"]))
    write_jsonl(calls_path, rows)
    if not quiet:
        found = ", ".join(f"{k} ({p})" for p, k in sources) or "none"
        print(f"Trace sources: {found}")
        print(f"Model calls stored: {len(rows)} ({len(rows) - before} new)")
        if not sources:
            print("No Copilot traces found. In VS Code, set github.copilot.chat.otel.dbSpanExporter.enabled "
                  "to true; for the Copilot CLI, start it with .github/token-tracker/copilot-tracked.sh.")
    for n in notes:
        print(f"warning: {n}", file=sys.stderr)
    return rows


# ── Attribution ──────────────────────────────────────────────────────────────────────────────────


def _branch_matches(branch, ticket):
    return bool(branch) and re.search(rf"(?<![A-Za-z0-9]){re.escape(ticket)}(?![0-9])", branch, re.IGNORECASE) is not None


def calls_for_ticket(calls, markers, ticket):
    """A chat belongs to a ticket if a marker for it was written while that chat was active (split at each
    marker when one chat covers several tickets), or, with no marker in that chat, if any of its turns ran
    on a branch named for the ticket."""
    sessions = {}
    for c in calls:
        sessions.setdefault(c["session"], []).append(c)
    picked = []
    for session_calls in sessions.values():
        session_calls.sort(key=lambda c: c["timestamp_ms"])
        first, last = session_calls[0]["timestamp_ms"], session_calls[-1]["timestamp_ms"]
        inside = sorted(
            (m for m in markers if first - SESSION_SLACK_MS <= m["timestamp_ms"] <= last + SESSION_SLACK_MS),
            key=lambda m: m["timestamp_ms"],
        )
        if inside:
            for c in session_calls:
                owner = inside[0]
                for m in inside:
                    if m["timestamp_ms"] <= c["timestamp_ms"]:
                        owner = m
                if owner["ticketId"].upper() == ticket.upper():
                    picked.append(c)
        elif any(_branch_matches(c.get("branch"), ticket) for c in session_calls):
            picked.extend(session_calls)
    return sorted(picked, key=lambda c: (c["timestamp_ms"], c["id"]))


# ── Commands ─────────────────────────────────────────────────────────────────────────────────────


def cmd_mark(root, ticket):
    path = tracker_dir(root) / MARKERS_FILE
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ticketId": ticket, "timestamp_ms": now_ms()}) + "\n")
    print(f"Token tracking: work on {ticket} marked as starting now.")


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(str(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def cmd_report(root, ticket):
    calls = collect(root)
    markers = load_jsonl(tracker_dir(root) / MARKERS_FILE)
    mine = calls_for_ticket(calls, markers, ticket)
    out_dir = tracker_dir(root) / ticket
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "token-usage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for c in mine:
            w.writerow([ticket, c["agentName"], c["model"], c["inputTokens"], c["outputTokens"], iso(c["timestamp_ms"])])

    total_in = sum(c["inputTokens"] for c in mine)
    total_out = sum(c["outputTokens"] for c in mine)
    lines = [f"# Token usage — {ticket}", ""]
    if not mine:
        lines += [
            "No model calls found for this ticket.",
            "",
            "Either tracing wasn't on while it was worked on, or none of its chats could be linked to it: a chat is "
            f"linked when `token_tracker.py mark {ticket}` ran during it, or when one of its turns ran on a branch "
            f"named for {ticket}.",
        ]
    else:
        per_agent, per_model = {}, {}
        for c in mine:
            for table, key in ((per_agent, c["agentName"]), (per_model, c["model"])):
                t = table.setdefault(key, [0, 0, 0])
                t[0] += 1
                t[1] += c["inputTokens"]
                t[2] += c["outputTokens"]
        lines += [
            f"- **Total:** {total_in + total_out:,} tokens ({total_in:,} input, {total_out:,} output) "
            f"across {len(mine)} model calls",
            f"- **Period:** {iso(mine[0]['timestamp_ms'])} to {iso(mine[-1]['timestamp_ms'])}",
            f"- **Sources:** {', '.join(sorted({c['source'] for c in mine}))}",
            "",
            "## By agent",
            "",
            _table(["Agent", "Calls", "Input tokens", "Output tokens", "Share"],
                   [(a, n, f"{i:,}", f"{o:,}", f"{(i + o) * 100 / max(total_in + total_out, 1):.1f}%")
                    for a, (n, i, o) in sorted(per_agent.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))]),
            "",
            "## By model",
            "",
            _table(["Model", "Calls", "Input tokens", "Output tokens"],
                   [(m, n, f"{i:,}", f"{o:,}") for m, (n, i, o) in sorted(per_model.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))]),
            "",
            "Skills and hooks make no model calls of their own: a skill's text is counted in the input tokens of "
            "the agent that loaded it, and hooks are scripts that use no tokens. Per-call rows are in "
            "`token-usage.csv`.",
        ]
    (out_dir / "token-usage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print()
    print("\n".join(lines))
    print()
    print(f"Written to {out_dir.relative_to(root) if out_dir.is_relative_to(root) else out_dir}/token-usage.md and token-usage.csv")


def ticket_arg(value):
    if not TICKET_ID.match(value):
        raise argparse.ArgumentTypeError(f"not a ticket ID: {value!r} (expected e.g. ABC-123)")
    return value.upper()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Per-ticket Copilot token usage.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("mark", help="record that work on a ticket starts now").add_argument("ticket", type=ticket_arg)
    sub.add_parser("collect", help="copy new model calls from Copilot's traces into .logs/token-tracker/")
    sub.add_parser("report", help="collect, then write a ticket's usage report").add_argument("ticket", type=ticket_arg)
    args = parser.parse_args(argv)
    root = repo_root()
    if args.command == "mark":
        cmd_mark(root, args.ticket)
    elif args.command == "collect":
        collect(root)
    else:
        cmd_report(root, args.ticket)


if __name__ == "__main__":
    main()
