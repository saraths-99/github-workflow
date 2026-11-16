"""Tests for .github/token-tracker/scripts/token_tracker.py. Run: python3 -m unittest tests/test_token_tracker.py"""
import csv
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "token-tracker" / "scripts" / "token_tracker.py"

# Same tables Copilot Chat creates (src/platform/otel/node/sqlite/otelSqliteStore.ts, schema version 1).
SCHEMA = """
CREATE TABLE spans (
    span_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, parent_span_id TEXT,
    name TEXT NOT NULL, start_time_ms INTEGER NOT NULL, end_time_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 0, status_message TEXT,
    operation_name TEXT, provider_name TEXT, agent_name TEXT, conversation_id TEXT,
    request_model TEXT, response_model TEXT,
    input_tokens INTEGER, output_tokens INTEGER, cached_tokens INTEGER, reasoning_tokens INTEGER,
    tool_name TEXT, tool_call_id TEXT, tool_type TEXT,
    chat_session_id TEXT, turn_index INTEGER, ttft_ms REAL
);
CREATE TABLE span_attributes (span_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT, PRIMARY KEY (span_id, key));
"""

T0 = 1_790_000_000_000  # ms
REMOTE = "https://bitbucket.org/acme/android-app.git"


def add_span(conn, span_id, parent, name, start, op, agent=None, conv=None, model=None, inp=None, out=None, attrs=None):
    conn.execute(
        "INSERT INTO spans (span_id, trace_id, parent_span_id, name, start_time_ms, end_time_ms, operation_name,"
        " agent_name, conversation_id, response_model, input_tokens, output_tokens) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (span_id, "trace-" + (conv or "x"), parent, name, start, start + 1, op, agent, conv, model, inp, out),
    )
    for k, v in (attrs or {}).items():
        conn.execute("INSERT INTO span_attributes VALUES (?,?,?)", (span_id, k, v))


class TokenTrackerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "app"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin", "git@bitbucket.org:acme/android-app.git"], check=True)
        self.db = Path(self.tmp.name) / "agent-traces.db"
        self.env = dict(os.environ, TOKEN_TRACKER_VSCODE_DB=str(self.db))

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, at_ms=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, check=True)

    def write_marker(self, ticket, ts):
        d = self.repo / ".logs" / "token-tracker"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "markers.jsonl", "a") as f:
            f.write(json.dumps({"ticketId": ticket, "timestamp_ms": ts}) + "\n")

    def read_csv(self, ticket):
        with open(self.repo / ".logs" / "token-tracker" / ticket / "token-usage.csv") as f:
            return list(csv.DictReader(f))

    def build_db(self):
        conn = sqlite3.connect(self.db)
        conn.executescript(SCHEMA)
        here = {"copilot_chat.repo.remote_url": REMOTE}
        # Chat 1: ABC-1, picked from the picker, with a sub-agent; linked by a marker.
        add_span(conn, "a1", None, "invoke_agent GitHub Copilot Chat", T0, "invoke_agent", "GitHub Copilot Chat", "conv-1",
                 attrs={**here, "copilot_chat.mode_name": "qatalyst-ticket", "copilot_chat.repo.head_branch_name": "develop"})
        add_span(conn, "c1", "a1", "chat gpt-5", T0 + 1000, "chat", model="gpt-5", inp=1000, out=100)
        add_span(conn, "t1", "a1", "execute_tool runSubagent", T0 + 2000, "execute_tool")
        add_span(conn, "a2", "t1", "invoke_agent qatalyst-bug-planner", T0 + 3000, "invoke_agent", "qatalyst-bug-planner", "conv-sub",
                 attrs=here)
        add_span(conn, "c2", "a2", "chat claude-sonnet", T0 + 4000, "chat", model="claude-sonnet", inp=500, out=50)
        add_span(conn, "c3", "a2", "chat claude-sonnet", T0 + 5000, "chat", model="claude-sonnet", inp=700, out=70)
        # Chat 2: no marker, but a turn ran on ABC-1's feature branch.
        add_span(conn, "a3", None, "invoke_agent GitHub Copilot Chat", T0 + 3_600_000, "invoke_agent", "GitHub Copilot Chat", "conv-2",
                 attrs={**here, "copilot_chat.repo.head_branch_name": "feature/ABC-1-fix-crash"})
        add_span(conn, "c4", "a3", "chat gpt-5", T0 + 3_601_000, "chat", model="gpt-5", inp=300, out=30)
        # Chat 3: another project's repo, on a branch that happens to match; must be ignored.
        add_span(conn, "a4", None, "invoke_agent GitHub Copilot Chat", T0 + 7_200_000, "invoke_agent", "GitHub Copilot Chat", "conv-3",
                 attrs={"copilot_chat.repo.remote_url": "https://github.com/other/repo",
                        "copilot_chat.repo.head_branch_name": "feature/ABC-1-other"})
        add_span(conn, "c5", "a4", "chat gpt-5", T0 + 7_201_000, "chat", model="gpt-5", inp=9999, out=999)
        # Chat 4: ABC-10 on its own branch; must not be mistaken for ABC-1.
        add_span(conn, "a5", None, "invoke_agent GitHub Copilot Chat", T0 + 9_000_000, "invoke_agent", "GitHub Copilot Chat", "conv-4",
                 attrs={**here, "copilot_chat.repo.head_branch_name": "feature/ABC-10-thing"})
        add_span(conn, "c6", "a5", "chat gpt-5", T0 + 9_001_000, "chat", model="gpt-5", inp=1, out=1)
        conn.commit()
        conn.close()

    def test_vscode_report(self):
        self.build_db()
        self.write_marker("ABC-1", T0 + 500)
        out = self.run_tool("report", "abc-1").stdout
        rows = self.read_csv("ABC-1")
        self.assertEqual(list(rows[0].keys()), ["ticketId", "agentName", "model", "inputTokens", "outputTokens", "timestamp"])
        self.assertEqual([(r["agentName"], r["inputTokens"]) for r in rows], [
            ("qatalyst-ticket", "1000"), ("qatalyst-bug-planner", "500"), ("qatalyst-bug-planner", "700"),
            ("GitHub Copilot Chat", "300"),
        ])
        self.assertTrue(all(r["ticketId"] == "ABC-1" for r in rows))
        self.assertEqual(rows[0]["timestamp"], "2026-09-21T14:13:21Z")
        self.assertIn("2,750 tokens (2,500 input, 250 output) across 4 model calls", out)
        stored = (self.repo / ".logs" / "token-tracker" / "calls.jsonl").read_text()
        self.assertNotIn("9999", stored)

    def test_rows_survive_copilot_cleanup(self):
        self.build_db()
        self.write_marker("ABC-1", T0 + 500)
        self.run_tool("collect")
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM spans")
        conn.commit()
        conn.close()
        self.run_tool("report", "ABC-1")
        self.assertEqual(len(self.read_csv("ABC-1")), 4)

    def test_cli_trace_file(self):
        d = self.repo / ".logs" / "token-tracker"
        d.mkdir(parents=True)
        otlp = {"resourceSpans": [{"scopeSpans": [{"spans": [
            {"traceId": "t", "spanId": "r", "name": "invoke_agent qatalyst-developer", "startTimeUnixNano": str((T0 + 10) * 1_000_000),
             "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "invoke_agent"}},
                            {"key": "gen_ai.agent.name", "value": {"stringValue": "qatalyst-developer"}},
                            {"key": "gen_ai.conversation.id", "value": {"stringValue": "cli-1"}}]},
            {"traceId": "t", "spanId": "k", "parentSpanId": "r", "name": "chat gpt-5", "startTimeUnixNano": str((T0 + 20) * 1_000_000),
             "attributes": [{"key": "gen_ai.operation.name", "value": {"stringValue": "chat"}},
                            {"key": "gen_ai.response.model", "value": {"stringValue": "gpt-5"}},
                            {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "40"}},
                            {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "4"}}]}]}]}]}
        sdk_style = {"name": "chat gpt-5", "_spanContext": {"traceId": "t", "spanId": "k2"}, "parentSpanContext": {"spanId": "r"},
                     "startTime": [(T0 + 30) // 1000, (T0 + 30) % 1000 * 1_000_000],
                     "attributes": {"gen_ai.operation.name": "chat", "gen_ai.response.model": "gpt-5",
                                    "gen_ai.usage.input_tokens": 60, "gen_ai.usage.output_tokens": 6}}
        (d / "copilot-cli-otel.jsonl").write_text(json.dumps(otlp) + "\n{}\n" + json.dumps(sdk_style) + "\n")
        self.write_marker("XY-7", T0)
        self.env["TOKEN_TRACKER_VSCODE_DB"] = str(Path(self.tmp.name) / "missing.db")
        self.run_tool("report", "XY-7")
        rows = self.read_csv("XY-7")
        self.assertEqual([(r["agentName"], r["inputTokens"], r["outputTokens"]) for r in rows],
                         [("qatalyst-developer", "40", "4"), ("qatalyst-developer", "60", "6")])

    def test_unreadable_trace_file_warns(self):
        d = self.repo / ".logs" / "token-tracker"
        d.mkdir(parents=True)
        (d / "copilot-cli-otel.jsonl").write_text("{}\n{}\n")
        self.env["TOKEN_TRACKER_VSCODE_DB"] = str(Path(self.tmp.name) / "missing.db")
        result = self.run_tool("collect")
        self.assertIn("2 lines but no readable trace records", result.stderr)

    def test_mark_and_bad_ticket_id(self):
        self.run_tool("mark", "abc-12")
        marker = json.loads((self.repo / ".logs" / "token-tracker" / "markers.jsonl").read_text())
        self.assertEqual(marker["ticketId"], "ABC-12")
        bad = subprocess.run([sys.executable, str(SCRIPT), "report", "../etc"], cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
