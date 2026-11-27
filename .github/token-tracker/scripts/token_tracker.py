#!/usr/bin/env python3
"""Per-ticket Copilot token usage, read from Copilot's own local traces.

  token_tracker.py mark <ticket ID>     record that work on a ticket starts now
  token_tracker.py collect              copy new model calls from Copilot's traces into .logs/
  token_tracker.py meta <ticket ID> [--title T] [--type TYPE]
                                        remember the ticket's title and Jira type for the report
  token_tracker.py report <ticket ID> [--open] [--final] [--prices SHEET.xlsx]
                                        collect, then write that ticket's usage report
                                        (.html, .json); --open shows the HTML page; --final
                                        stamps the ticket's end time; --prices is a model price
                                        sheet used only for calls Copilot gave no cost for

Sources: VS Code Copilot Chat's local trace database (agent-traces.db, enabled by the
`github.copilot.chat.otel.dbSpanExporter.enabled` setting) and the Copilot CLI's JSON-lines trace
file, if one is present. Meant for VS Code only; the workflow runs it nowhere else. macOS and Linux only.
Standard library only.
"""
import argparse
import html
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
ATTR_CACHE_READ = "gen_ai.usage.cache_read.input_tokens"
ATTR_CACHE_WRITE = "gen_ai.usage.cache_creation.input_tokens"
# Copilot's own cost for the call, in billionths of an AI credit (1 AI credit = $0.01).
ATTR_NANO_AIU = "copilot_chat.copilot_usage_nano_aiu"
META_FILE = "tickets.json"
USD_PER_CREDIT = 0.01


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


def candidate_db_paths():
    override = os.environ.get("TOKEN_TRACKER_VSCODE_DB")
    if override:
        return [Path(override)]
    base = (Path.home() / "Library" / "Application Support" if sys.platform == "darwin"
            else Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
    return [base / product / "User" / "globalStorage" / "github.copilot-chat" / "agent-traces.db"
            for product in ("Code", "Code - Insiders", "VSCodium")]


def vscode_db_paths():
    override = os.environ.get("TOKEN_TRACKER_VSCODE_DB")
    if override:
        return [Path(override)] if Path(override).is_file() else []
    home = Path.home()
    if sys.platform == "darwin":
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
                "SELECT span_id, key, value FROM span_attributes WHERE key IN (?, ?, ?, ?, ?, ?)",
                (ATTR_MODE, ATTR_BRANCH, ATTR_REMOTE, ATTR_CACHE_READ, ATTR_CACHE_WRITE, ATTR_NANO_AIU),
            ):
                attrs.setdefault(span_id, {})[key] = value
            spans = []
            for row in conn.execute(
                "SELECT span_id, trace_id, parent_span_id, name, start_time_ms, operation_name, agent_name,"
                " conversation_id, chat_session_id, request_model, response_model, input_tokens, output_tokens,"
                " cached_tokens FROM spans"
            ):
                (span_id, trace_id, parent, name, start, op, agent, conv, chat_session,
                 req_model, resp_model, inp, out, cached_col) = row
                a = attrs.get(span_id, {})
                spans.append({
                    "id": span_id, "trace": trace_id, "parent": parent, "name": name or "",
                    "start_ms": int(start or 0), "op": op, "agent": agent, "mode": a.get(ATTR_MODE),
                    "conv": conv or chat_session, "branch": a.get(ATTR_BRANCH), "remote": a.get(ATTR_REMOTE),
                    "model": resp_model or req_model, "inp": inp, "out": out,
                    "cached": _int_or_none(a.get(ATTR_CACHE_READ)) if a.get(ATTR_CACHE_READ) is not None else cached_col,
                    "cache_write": _int_or_none(a.get(ATTR_CACHE_WRITE)),
                    "aiu": _int_or_none(a.get(ATTR_NANO_AIU)),
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
        "cached": _int_or_none(a.get(ATTR_CACHE_READ)),
        "cache_write": _int_or_none(a.get(ATTR_CACHE_WRITE)),
        "aiu": _int_or_none(a.get(ATTR_NANO_AIU)),
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
            "cachedInputTokens": s.get("cached"),
            "cacheWriteTokens": s.get("cache_write"),
            "nanoAiu": s.get("aiu"),
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


LAST_COLLECT = {}


def collect(root, quiet=False):
    tdir = tracker_dir(root)
    this_repo = current_remote(root)
    calls_path = tdir / CALLS_FILE
    stored = {c["id"]: c for c in load_jsonl(calls_path)}
    before = len(stored)
    notes = []
    info = LAST_COLLECT
    info.clear()
    info.update({"sources": [], "read": 0, "other_repo": 0, "errors": []})

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
            info["errors"].append(f"{path}: {e}")
            continue
        calls = spans_to_calls(spans, kind)
        info["sources"].append(f"{kind}: {path}")
        info["read"] += len(calls)
        sessions_elsewhere = {c["session"] for c in calls if this_repo and c["remote"] and c["remote"] != this_repo}
        sessions_here = {c["session"] for c in calls if this_repo and c["remote"] == this_repo}
        for c in calls:
            if c["session"] in sessions_elsewhere and c["session"] not in sessions_here:
                info["other_repo"] += 1
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
                  "to true.")
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


HTML_STYLE = """
:root { --bg:#f7f7f5; --surface:#fff; --text:#1f1f1d; --muted:#6b6a65; --border:#e4e3de;
        --accent:#4b5bd6; --accent-soft:#e3e6fb; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#1b1b1a; --surface:#252523; --text:#ecebe6; --muted:#a3a29b; --border:#3a3936;
          --accent:#8c98f0; --accent-soft:#2f3359; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
       font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:980px; margin:0 auto; padding:32px 16px 48px; }
.eyebrow { margin:0; color:var(--muted); font-size:13px; letter-spacing:.02em; }
h1 { margin:2px 0 4px; font-size:28px; font-weight:600; }
h2 { margin:32px 0 10px; font-size:17px; font-weight:600; }
.meta { margin:0; color:var(--muted); font-size:14px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-top:24px; }
.tile, .card { background:var(--surface); border:1px solid var(--border); border-radius:10px; }
.tile { padding:14px 16px; }
.tile .label { color:var(--muted); font-size:13px; }
.tile .value { font-size:26px; font-weight:600; font-variant-numeric:tabular-nums; }
.card { overflow-x:auto; }
table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { padding:9px 14px; text-align:left; border-bottom:1px solid var(--border); white-space:nowrap; }
th { color:var(--muted); font-weight:500; font-size:13px; }
tr:last-child td { border-bottom:none; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.share { display:flex; align-items:center; gap:10px; min-width:170px; }
.bar { flex:1; height:8px; background:var(--accent-soft); border-radius:4px; overflow:hidden; }
.bar span { display:block; height:100%; background:var(--accent); }
.share .pct { width:48px; text-align:right; font-variant-numeric:tabular-nums; color:var(--muted); }
@media (max-width:600px) { .bar { display:none; } .share { min-width:0; } }
.empty { padding:20px; color:var(--muted); }
footer { margin-top:28px; color:var(--muted); font-size:13px; }
code { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12.5px; }
"""


def render_html(summary, sources):
    """Static page from the same data as token-usage.json; every value is escaped, and there are no scripts."""
    e = html.escape
    ticket, totals, calls = summary["ticketId"], summary["totals"], summary["calls"]
    grand = max(totals["totalTokens"], 1)

    def share_cell(tokens):
        pct = tokens * 100 / grand
        return (f'<td><div class="share"><div class="bar"><span style="width:{pct:.1f}%"></span></div>'
                f'<span class="pct">{pct:.1f}%</span></div></td>')

    def readable(ts):
        return ts.replace("T", " ").replace("Z", " UTC")

    by_model = {}
    for c in calls:
        m = by_model.setdefault(c["model"], {"calls": 0, "inputTokens": 0, "outputTokens": 0, "cost": 0.0})
        m["calls"] += 1
        m["inputTokens"] += c["inputTokens"]
        m["outputTokens"] += c["outputTokens"]
        m["cost"] += c["cost"] or 0.0

    def money(x):
        return "n/a" if x is None else f"${x:,.4f}"

    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Token usage: {e(ticket)}</title><style>{HTML_STYLE}</style></head><body><main>",
        f'<p class="eyebrow">Copilot token usage</p><h1>{e(ticket)}</h1>',
    ]
    if not calls:
        parts += [
            '<p class="meta">No model calls found for this ticket.</p>',
            '<div class="card" style="margin-top:24px"><p class="empty">Either tracing wasn\'t on while it was worked '
            f"on, or none of its chats could be linked to it: a chat is linked when "
            f"<code>token_tracker.py mark {e(ticket)}</code> ran during it, or when one of its turns ran on a branch "
            f"named for {e(ticket)}.</p></div>",
        ]
    else:
        parts += [
            f'<p class="meta">{e(readable(calls[0]["timestamp"]))} to {e(readable(calls[-1]["timestamp"]))}'
            f" · from {e(', '.join(sources))}</p>",
            '<section class="tiles">',
        ]
        for label, value in (("Total tokens", f"{totals['totalTokens']:,}"), ("Input tokens", f"{totals['inputTokens']:,}"),
                             ("Output tokens", f"{totals['outputTokens']:,}"), ("Model calls", f"{totals['calls']:,}"),
                             ("Cost (USD)", money(totals["cost"])),
                             ("AI credits", f"{totals['cost'] / USD_PER_CREDIT:,.2f}")):
            parts.append(f'<div class="tile"><div class="label">{label}</div><div class="value">{value}</div></div>')
        parts += [
            "</section>",
            '<h2>By agent</h2><div class="card"><table><thead><tr><th>Agent</th><th>Share of tokens</th>'
            '<th class="num">Calls</th><th class="num">Input</th><th class="num">Output</th><th class="num">Total</th>'
            '<th class="num">Cost (USD)</th></tr></thead><tbody>',
        ]
        for a in summary["byAgent"]:
            parts.append(
                f'<tr><td>{e(a["agentName"])}</td>{share_cell(a["totalTokens"])}<td class="num">{a["calls"]:,}</td>'
                f'<td class="num">{a["inputTokens"]:,}</td><td class="num">{a["outputTokens"]:,}</td>'
                f'<td class="num">{a["totalTokens"]:,}</td><td class="num">{money(a["cost"])}</td></tr>'
            )
        parts.append(
            '</tbody></table></div><h2>By model</h2><div class="card"><table><thead><tr><th>Model</th>'
            '<th>Share of tokens</th><th class="num">Calls</th><th class="num">Input</th><th class="num">Output</th>'
            '<th class="num">Cost (USD)</th></tr></thead><tbody>'
        )
        for model, m in sorted(by_model.items(), key=lambda kv: (-(kv[1]["inputTokens"] + kv[1]["outputTokens"]), kv[0])):
            parts.append(
                f'<tr><td>{e(model)}</td>{share_cell(m["inputTokens"] + m["outputTokens"])}'
                f'<td class="num">{m["calls"]:,}</td><td class="num">{m["inputTokens"]:,}</td>'
                f'<td class="num">{m["outputTokens"]:,}</td><td class="num">{money(m["cost"])}</td></tr>'
            )
        parts.append(
            '</tbody></table></div><h2>Every model call</h2><div class="card"><table><thead><tr><th>Time</th>'
            '<th>Agent</th><th>Model</th><th class="num">Input</th><th class="num">Cached</th>'
            '<th class="num">Output</th><th class="num">Cost (USD)</th></tr></thead><tbody>'
        )
        for c in calls:
            parts.append(
                f'<tr><td>{e(readable(c["timestamp"]))}</td><td>{e(c["agentName"])}</td><td>{e(c["model"])}</td>'
                f'<td class="num">{c["inputTokens"]:,}</td>'
                f'<td class="num">{"n/a" if c.get("cachedInputTokens") is None else format(c["cachedInputTokens"], ",")}</td>'
                f'<td class="num">{c["outputTokens"]:,}</td><td class="num">{money(c["cost"])}</td></tr>'
            )
        parts += [
            "</tbody></table></div>",
            "<footer>Skills make no model calls of their own: a skill's text is counted in the input "
            "tokens of the agent that loaded it. Input includes the cached tokens. Cost is Copilot's own figure "
            "for each call where it recorded one. Same data as "
            "<code>token-usage.json</code> in this folder.</footer>",
        ]
    parts.append("</main></body></html>\n")
    return "".join(parts)


def open_in_browser(path):
    """Opens the page with the OS's own handler; returns False where there's no local display to show it on."""
    try:
        if sys.platform == "darwin":
            if os.environ.get("SSH_CONNECTION"):
                return False
            opener = ["open"]
        else:
            if os.environ.get("SSH_CONNECTION") or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                return False
            if not shutil.which("xdg-open"):
                return False
            opener = ["xdg-open"]
        subprocess.Popen([*opener, str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def why_empty(root, ticket, calls, markers):
    """One line per fact that explains an empty report, most basic first."""
    info = LAST_COLLECT
    out = []
    if not info.get("sources"):
        out.append("No Copilot trace database was found, so nothing could be read. In VS Code, "
                   "github.copilot.chat.otel.dbSpanExporter.enabled must be true (workspace or user settings), and "
                   "VS Code must be reloaded after it is turned on. Searched: "
                   + ", ".join(str(p) for p in candidate_db_paths()) + " (none present)."
                   if not vscode_db_paths() else "A trace database exists but could not be read.")
        for e in info.get("errors", []):
            out.append(f"Read error: {e}")
        return out
    out.append("Trace sources read: " + "; ".join(info["sources"]))
    if info["read"] == 0:
        out.append("The database has no model calls in it. Tracing was probably switched on after the chats ran; "
                   "only chats held after the setting is on and VS Code reloaded are recorded.")
        return out
    out.append(f"Model calls read: {info['read']}; stored in total: {len(calls)}.")
    if info["other_repo"]:
        out.append(f"{info['other_repo']} calls were skipped because their chat ran in a different git repository "
                   "(a different remote from this one).")
    mine_markers = [m for m in markers if m["ticketId"].upper() == ticket.upper()]
    out.append(f"Markers for {ticket}: {len(mine_markers)}"
               + ("" if mine_markers else " (token_tracker.py mark was never run for it on this machine)") + ".")
    if calls:
        sessions = {}
        for c in calls:
            sessions.setdefault(c["session"], []).append(c)
        branches = sorted({c["branch"] for c in calls if c.get("branch")})
        out.append(f"{len(sessions)} chats stored, spanning {iso(min(c['timestamp_ms'] for c in calls))} to "
                   f"{iso(max(c['timestamp_ms'] for c in calls))}; branches seen in them: "
                   + (", ".join(branches[:8]) if branches else "none recorded") + ".")
        if mine_markers:
            out.append("A marker only links a chat whose calls fall within the chat's time span (plus a small slack). "
                       f"Marker times: {', '.join(iso(m['timestamp_ms']) for m in mine_markers[-3:])}.")
    return out


# ── Cost and the usage document ──────────────────────────────────────────────────────────────────


def meta_path(root):
    return tracker_dir(root) / META_FILE


def load_meta(root):
    try:
        return json.loads(meta_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_meta(root, ticket, **fields):
    data = load_meta(root)
    entry = data.setdefault(ticket, {})
    entry.update({k: v for k, v in fields.items() if v is not None})
    tmp = meta_path(root).with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, meta_path(root))


def git_identity(root):
    def get(key):
        try:
            out = subprocess.run(["git", "-C", str(root), "config", key], capture_output=True, text=True, check=True)
            return out.stdout.strip() or None
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"name": get("user.name"), "email": get("user.email")}


def load_prices(path):
    """The price sheet as {model: rows}, or None when there is none or it can't be read."""
    path = path or os.environ.get("TOKEN_TRACKER_PRICES")
    if not path:
        return None
    try:
        import token_credits
        rates, problems = token_credits.load_rates(path)
    except Exception as e:  # noqa: BLE001 - a bad sheet must never stop the report
        print(f"warning: price sheet {path} not used ({e})", file=sys.stderr)
        return None
    for note in problems:
        print(f"warning: {note}", file=sys.stderr)
    return rates


def token_split(c):
    """(fresh input, cache read, cache write) for a stored call. `inputTokens` as Copilot records it holds all
    three; when the cache figures weren't recorded, everything counts as fresh and the other two are None."""
    total = c["inputTokens"]
    cached, write = c.get("cachedInputTokens"), c.get("cacheWriteTokens")
    if cached is None and write is None:
        return total, None, None
    cached, write = cached or 0, write or 0
    return max(total - cached - write, 0), cached, write


def estimate_cost(c, rates):
    """USD from the price sheet, or None if the model isn't in it. Only used when Copilot gave no cost. Two
    behaviours were checked against Copilot's own figures: input beyond the cache reads is billed at the
    Cache write rate when the sheet has one and Copilot reported no explicit cache write (the OpenAI
    models), and at the Input rate with the cache write billed separately when it did (Anthropic)."""
    import token_credits
    r = token_credits.pick_rate(rates, c["model"], c["inputTokens"])
    if r is None:
        return None
    fresh, cached, write = token_split(c)
    cached = cached or 0
    cached_rate = r["cached"] if r["cached"] is not None else r["input"]
    if c.get("cacheWriteTokens") is not None:
        usd = fresh * r["input"] + write * (r["write"] if r["write"] is not None else r["input"])
    else:
        usd = fresh * (r["write"] if r["write"] is not None else r["input"])
    usd += cached * cached_rate + c["outputTokens"] * r["output"]
    return usd / 1_000_000


def call_cost(c, rates):
    """(USD, source): Copilot's own figure when it recorded one, else the price-sheet estimate, else (None, None)."""
    if c.get("nanoAiu") is not None:
        return c["nanoAiu"] / 1e9 * USD_PER_CREDIT, "copilot"
    if rates:
        usd = estimate_cost(c, rates)
        if usd is not None:
            return usd, "sheet"
    return None, None


def build_usage_doc(root, ticket, mine, rates, stamp):
    """The token-usage.json document: the ticket, then one step per agent, each with its calls and cost."""
    meta = load_meta(root).get(ticket, {})
    steps, order = {}, []
    for c in mine:
        name = c["agentName"]
        if name not in steps:
            steps[name] = []
            order.append(name)
        usd, _ = call_cost(c, rates)
        fresh, cached, write = token_split(c)
        steps[name].append({
            "agentName": name, "model": c["model"], "timestamp": iso(c["timestamp_ms"]),
            "inputTokens": fresh, "cachedInputTokens": cached, "cacheWriteTokens": write,
            "outputTokens": c["outputTokens"], "totalCost": None if usd is None else round(usd, 10),
        })
    out_steps = []
    for name in order:
        costs = [x["totalCost"] for x in steps[name] if x["totalCost"] is not None]
        out_steps.append({"stepName": name, "totalCost": round(float(sum(costs)), 10), "calls": steps[name]})
    all_costs = [x["totalCost"] for st in out_steps for x in st["calls"] if x["totalCost"] is not None]
    return {
        "ticketId": ticket,
        "executionDatetime": stamp,
        "ticketTitle": meta.get("title"),
        "ticketType": meta.get("type"),
        "executor": git_identity(root),
        "priceUnit": "USD",
        "totalCost": round(float(sum(all_costs)), 10),
        "startTime": iso(mine[0]["timestamp_ms"]) if mine else None,
        "endTime": meta.get("endedAt"),
        "steps": out_steps,
    }


def cmd_report(root, ticket, open_page=False, final=False, prices=None):
    calls = collect(root)
    markers = load_jsonl(tracker_dir(root) / MARKERS_FILE)
    mine = calls_for_ticket(calls, markers, ticket)
    out_dir = tracker_dir(root) / ticket
    out_dir.mkdir(parents=True, exist_ok=True)
    rates = load_prices(prices)
    stamp = iso(now_ms())
    if final:
        save_meta(root, ticket, endedAt=stamp)

    rows, unpriced = [], 0
    for c in mine:
        usd, _ = call_cost(c, rates)
        unpriced += usd is None
        rows.append({"agentName": c["agentName"], "model": c["model"], "inputTokens": c["inputTokens"],
                     "outputTokens": c["outputTokens"], "cachedInputTokens": c.get("cachedInputTokens"),
                     "cost": usd, "timestamp": iso(c["timestamp_ms"])})
    total_in = sum(r["inputTokens"] for r in rows)
    total_out = sum(r["outputTokens"] for r in rows)
    total_cost = sum(r["cost"] for r in rows if r["cost"] is not None)
    by_agent = {}
    for r in rows:
        a = by_agent.setdefault(r["agentName"], {"agentName": r["agentName"], "calls": 0, "inputTokens": 0,
                                                 "outputTokens": 0, "cost": 0.0})
        a["calls"] += 1
        a["inputTokens"] += r["inputTokens"]
        a["outputTokens"] += r["outputTokens"]
        a["cost"] += r["cost"] or 0.0
    for a in by_agent.values():
        a["totalTokens"] = a["inputTokens"] + a["outputTokens"]
    summary = {
        "ticketId": ticket,
        "totals": {"calls": len(rows), "inputTokens": total_in, "outputTokens": total_out,
                   "totalTokens": total_in + total_out, "cost": total_cost, "unpricedCalls": unpriced},
        "byAgent": sorted(by_agent.values(), key=lambda a: (-a["totalTokens"], a["agentName"])),
        "calls": rows,
    }
    doc = build_usage_doc(root, ticket, mine, rates, stamp)
    (out_dir / "token-usage.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    # Printed only, as the summary an agent passes on; the files are the .html and .json.
    lines = [f"# Token usage — {ticket}", ""]
    if not mine:
        lines += [
            "No model calls found for this ticket.",
            "",
            "Either tracing wasn't on while it was worked on, or none of its chats could be linked to it: a chat is "
            f"linked when `token_tracker.py mark {ticket}` ran during it, or when one of its turns ran on a branch "
            f"named for {ticket}.",
            "",
            "What this machine's data shows:",
        ] + [f"- {r}" for r in why_empty(root, ticket, calls, markers)]
    else:
        per_agent, per_model = {}, {}
        for r in rows:
            for table, key in ((per_agent, r["agentName"]), (per_model, r["model"])):
                t = table.setdefault(key, [0, 0, 0, 0.0])
                t[0] += 1
                t[1] += r["inputTokens"]
                t[2] += r["outputTokens"]
                t[3] += r["cost"] or 0.0
        lines += [
            f"- **Total:** {total_in + total_out:,} tokens ({total_in:,} input, {total_out:,} output) "
            f"across {len(mine)} model calls",
            f"- **Cost:** ${total_cost:,.4f} ({total_cost / USD_PER_CREDIT:,.2f} AI credits)"
            + (f", not counting {unpriced} calls with no cost (Copilot gave none and no price sheet covers them)"
               if unpriced else ""),
            f"- **Period:** {iso(mine[0]['timestamp_ms'])} to {iso(mine[-1]['timestamp_ms'])}",
            f"- **Sources:** {', '.join(sorted({c['source'] for c in mine}))}",
            "",
            "## By agent",
            "",
            _table(["Agent", "Calls", "Input tokens", "Output tokens", "Cost (USD)", "Share"],
                   [(a, n, f"{i:,}", f"{o:,}", f"{usd:,.4f}", f"{(i + o) * 100 / max(total_in + total_out, 1):.1f}%")
                    for a, (n, i, o, usd) in sorted(per_agent.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))]),
            "",
            "## By model",
            "",
            _table(["Model", "Calls", "Input tokens", "Output tokens", "Cost (USD)"],
                   [(m, n, f"{i:,}", f"{o:,}", f"{usd:,.4f}")
                    for m, (n, i, o, usd) in sorted(per_model.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))]),
            "",
            "Skills make no model calls of their own: a skill's text is counted in the input tokens of "
            "the agent that loaded it. Cost is Copilot's own figure for each call where it recorded one. "
            "Per-call rows, with the cache split, are in `token-usage.html` and `token-usage.json`.",
        ]
    page = out_dir / "token-usage.html"
    page.write_text(render_html(summary, sorted({c["source"] for c in mine})), encoding="utf-8")
    print()
    print("\n".join(lines))
    print()
    print(f"Written to {out_dir.relative_to(root) if out_dir.is_relative_to(root) else out_dir}/: token-usage.html, token-usage.json")
    if open_page:
        if open_in_browser(page):
            print(f"Opened {page} in your browser.")
        else:
            print(f"Couldn't open a browser from here; open {page} to see the report.")


def ticket_arg(value):
    if not TICKET_ID.match(value):
        raise argparse.ArgumentTypeError(f"not a ticket ID: {value!r} (expected e.g. ABC-123)")
    return value.upper()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Per-ticket Copilot token usage.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("mark", help="record that work on a ticket starts now").add_argument("ticket", type=ticket_arg)
    sub.add_parser("collect", help="copy new model calls from Copilot's traces into .logs/token-tracker/")
    meta = sub.add_parser("meta", help="remember a ticket's title and Jira issue type for its report")
    meta.add_argument("ticket", type=ticket_arg)
    meta.add_argument("--title")
    meta.add_argument("--type", dest="issue_type")
    report = sub.add_parser("report", help="collect, then write a ticket's usage report")
    report.add_argument("ticket", type=ticket_arg)
    report.add_argument("--open", action="store_true", help="open token-usage.html in the default browser")
    report.add_argument("--final", action="store_true", help="stamp the ticket's end time (the work is committed)")
    report.add_argument("--prices", help="model price sheet (.xlsx), used only for calls Copilot recorded no cost for")
    args = parser.parse_args(argv)
    root = repo_root()
    if args.command == "mark":
        cmd_mark(root, args.ticket)
    elif args.command == "collect":
        collect(root)
    elif args.command == "meta":
        save_meta(root, args.ticket, title=args.title, type=args.issue_type)
    else:
        cmd_report(root, args.ticket, open_page=args.open, final=args.final, prices=args.prices)


if __name__ == "__main__":
    main()
