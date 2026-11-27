"""Tests for .github/token-tracker/scripts/token_tracker.py. Run: python3 -m unittest tests/test_token_tracker.py"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "token-tracker" / "scripts" / "token_tracker.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_token_credits import make_xlsx  # noqa: E402  (a minimal .xlsx writer for the price-sheet tests)

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
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test Dev"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "dev@example.test"], check=True)
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

    def read_doc(self, ticket):
        return json.loads((self.repo / ".logs" / "token-tracker" / ticket / "token-usage.json").read_text())

    def read_rows(self, ticket):
        return [c for step in self.read_doc(ticket)["steps"] for c in step["calls"]]

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
        doc = self.read_doc("ABC-1")
        rows = self.read_rows("ABC-1")
        self.assertEqual(list(rows[0].keys()), ["agentName", "model", "timestamp", "inputTokens", "cachedInputTokens",
                                                 "cacheWriteTokens", "outputTokens", "totalCost"])
        # Steps are the agents, in the order they first appear.
        self.assertEqual([(st["stepName"], len(st["calls"])) for st in doc["steps"]],
                         [("qatalyst-ticket", 1), ("qatalyst-bug-planner", 2), ("GitHub Copilot Chat", 1)])
        self.assertEqual([r["inputTokens"] for r in rows], [1000, 500, 700, 300])
        self.assertEqual(rows[0]["timestamp"], "2026-09-21T14:13:21Z")
        # No cache figures were recorded for these spans, and no cost: unknown, never zero.
        self.assertTrue(all(r["cachedInputTokens"] is None and r["totalCost"] is None for r in rows))
        self.assertEqual(doc["ticketId"], "ABC-1")
        self.assertEqual(doc["priceUnit"], "USD")
        self.assertEqual(doc["totalCost"], 0.0)
        self.assertEqual(doc["executor"], {"name": "Test Dev", "email": "dev@example.test"})
        self.assertEqual((doc["ticketTitle"], doc["ticketType"], doc["endTime"]), (None, None, None))
        self.assertEqual(doc["startTime"], "2026-09-21T14:13:21Z")
        self.assertIn("2,750 tokens (2,500 input, 250 output) across 4 model calls", out)
        self.assertIn("not counting 4 calls with no cost", out)
        self.assertEqual(sorted(p.name for p in (self.repo / ".logs" / "token-tracker" / "ABC-1").iterdir()),
                         ["token-usage.html", "token-usage.json"])
        stored = (self.repo / ".logs" / "token-tracker" / "calls.jsonl").read_text()
        self.assertNotIn("9999", stored)

    def build_cost_db(self):
        conn = sqlite3.connect(self.db)
        conn.executescript(SCHEMA)
        here = {"copilot_chat.repo.remote_url": REMOTE}
        add_span(conn, "a1", None, "invoke_agent qatalyst-developer", T0, "invoke_agent", "qatalyst-developer", "conv-1", attrs=here)
        # Anthropic-style: input holds fresh + cache read + cache write; Copilot priced it at 1 credit ($0.01).
        add_span(conn, "c1", "a1", "chat claude-sonnet-5.5", T0 + 1000, "chat", model="claude-sonnet-5.5", inp=1000, out=100,
                 attrs={"gen_ai.usage.cache_read.input_tokens": "700", "gen_ai.usage.cache_creation.input_tokens": "200",
                        "copilot_chat.copilot_usage_nano_aiu": "1000000000"})
        # OpenAI-style: no cache write reported; Copilot priced it at half a credit.
        add_span(conn, "c2", "a1", "chat gpt-6-luna", T0 + 2000, "chat", model="gpt-6-luna", inp=500, out=50,
                 attrs={"gen_ai.usage.cache_read.input_tokens": "400", "copilot_chat.copilot_usage_nano_aiu": "500000000"})
        # A free helper call: Copilot recorded 0.
        add_span(conn, "c3", "a1", "chat gpt-4o-mini", T0 + 3000, "chat", model="gpt-4o-mini-2024-07-18", inp=100, out=10,
                 attrs={"gen_ai.usage.cache_read.input_tokens": "0", "copilot_chat.copilot_usage_nano_aiu": "0"})
        # No cost recorded for this one (a price sheet may cover it).
        add_span(conn, "c4", "a1", "chat claude-opus-5.5", T0 + 4000, "chat", model="claude-opus-5.5", inp=1_000_000, out=10_000,
                 attrs={"gen_ai.usage.cache_read.input_tokens": "600000", "gen_ai.usage.cache_creation.input_tokens": "100000"})
        add_span(conn, "c5", "a1", "chat gpt-6-luna", T0 + 5000, "chat", model="gpt-6-luna", inp=2000, out=100,
                 attrs={"gen_ai.usage.cache_read.input_tokens": "1500"})
        conn.commit()
        conn.close()

    def test_cache_split_and_copilots_own_cost(self):
        self.build_cost_db()
        self.write_marker("ABC-2", T0 + 500)
        self.run_tool("report", "ABC-2")
        rows = self.read_rows("ABC-2")
        # inputTokens is the fresh part: total minus cache read minus cache write.
        self.assertEqual([(r["inputTokens"], r["cachedInputTokens"], r["cacheWriteTokens"], r["outputTokens"]) for r in rows[:3]],
                         [(100, 700, 200, 100), (100, 400, 0, 50), (100, 0, 0, 10)])
        self.assertEqual([r["totalCost"] for r in rows[:3]], [0.01, 0.005, 0.0])
        self.assertIsNone(rows[3]["totalCost"])
        doc = self.read_doc("ABC-2")
        self.assertEqual(doc["steps"][0]["totalCost"], 0.015)
        self.assertEqual(doc["totalCost"], 0.015)

    def test_price_sheet_prices_only_calls_without_copilots_figure(self):
        self.build_cost_db()
        self.write_marker("ABC-2", T0 + 500)
        sheet = Path(self.tmp.name) / "prices.xlsx"
        header = ["Model", "Release status", "Category", "Tier", "Threshold (input tokens)", "Input", "Cached input", "Cache write", "Output"]
        make_xlsx(sheet, header=header, rows=[
            ["Claude Opus 5.5", "GA", "Powerful", "Default", "Not applicable", 4.0, 0.2, 5.0, 20.0],
            ["GPT-6 Luna", "GA", "Lightweight", "Default", "≤ 272K", 0.1, 0.01, 0.125, 0.5],
            ["Claude Sonnet 5.5", "GA", "Versatile", "Default", "Not applicable", 2.0, 0.1, 2.5, 10.0]])
        self.run_tool("report", "ABC-2", "--prices", str(sheet))
        rows = self.read_rows("ABC-2")
        # Copilot's own figures are kept as they are, not recomputed from the sheet.
        self.assertEqual([r["totalCost"] for r in rows[:3]], [0.01, 0.005, 0.0])
        # Opus: 300k fresh x $4 + 100k write x $5 + 600k read x $0.2 + 10k out x $20, per million.
        self.assertAlmostEqual(rows[3]["totalCost"], 1.2 + 0.5 + 0.12 + 0.2, places=9)
        # Luna with no explicit cache write: 500 fresh at the write rate, 1500 read, 100 out.
        self.assertAlmostEqual(rows[4]["totalCost"], (500 * 0.125 + 1500 * 0.01 + 100 * 0.5) / 1e6, places=12)

    def test_meta_and_final_stamp(self):
        self.build_cost_db()
        self.write_marker("ABC-2", T0 + 500)
        self.run_tool("meta", "abc-2", "--title", "Lock won't connect", "--type", "Bug")
        self.run_tool("report", "ABC-2")
        doc = self.read_doc("ABC-2")
        self.assertEqual((doc["ticketTitle"], doc["ticketType"], doc["endTime"]), ("Lock won't connect", "Bug", None))
        self.run_tool("report", "ABC-2", "--final")
        ended = self.read_doc("ABC-2")["endTime"]
        self.assertRegex(ended, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.run_tool("report", "ABC-2")          # a later plain report keeps the end time
        self.assertEqual(self.read_doc("ABC-2")["endTime"], ended)

    def test_rows_survive_copilot_cleanup(self):
        self.build_db()
        self.write_marker("ABC-1", T0 + 500)
        self.run_tool("collect")
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM spans")
        conn.commit()
        conn.close()
        self.run_tool("report", "ABC-1")
        self.assertEqual(len(self.read_rows("ABC-1")), 4)

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
        rows = self.read_rows("XY-7")
        self.assertEqual([(r["agentName"], r["inputTokens"], r["outputTokens"]) for r in rows],
                         [("qatalyst-developer", 40, 4), ("qatalyst-developer", 60, 6)])

    def test_unreadable_trace_file_warns(self):
        d = self.repo / ".logs" / "token-tracker"
        d.mkdir(parents=True)
        (d / "copilot-cli-otel.jsonl").write_text("{}\n{}\n")
        self.env["TOKEN_TRACKER_VSCODE_DB"] = str(Path(self.tmp.name) / "missing.db")
        result = self.run_tool("collect")
        self.assertIn("2 lines but no readable trace records", result.stderr)

    def test_html_page(self):
        self.build_db()
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE spans SET agent_name = '<script>alert(1)</script>' WHERE span_id = 'a2'")
        conn.commit()
        conn.close()
        self.write_marker("ABC-1", T0 + 500)
        env = {k: v for k, v in self.env.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        self.env = dict(env, SSH_CONNECTION="test")
        out = self.run_tool("report", "ABC-1", "--open").stdout
        self.assertIn("Couldn't open a browser from here; open", out)
        page = (self.repo / ".logs" / "token-tracker" / "ABC-1" / "token-usage.html").read_text()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertNotIn("<script", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn('<div class="value">2,750</div>', page)
        self.assertIn("2026-09-21 14:13:21 UTC", page)
        self.assertEqual(page.count("<tr><td>2026-"), 4)

    def test_ticket_with_no_calls(self):
        self.env["TOKEN_TRACKER_VSCODE_DB"] = str(Path(self.tmp.name) / "missing.db")
        self.run_tool("report", "NONE-1")
        doc = json.loads((self.repo / ".logs" / "token-tracker" / "NONE-1" / "token-usage.json").read_text())
        self.assertEqual({k: doc[k] for k in ("ticketId", "priceUnit", "totalCost", "startTime", "endTime", "steps")},
                         {"ticketId": "NONE-1", "priceUnit": "USD", "totalCost": 0.0, "startTime": None, "endTime": None, "steps": []})
        page = (self.repo / ".logs" / "token-tracker" / "NONE-1" / "token-usage.html").read_text()
        self.assertIn("No model calls found for this ticket.", page)

    def test_mark_and_bad_ticket_id(self):
        self.run_tool("mark", "abc-12")
        marker = json.loads((self.repo / ".logs" / "token-tracker" / "markers.jsonl").read_text())
        self.assertEqual(marker["ticketId"], "ABC-12")
        bad = subprocess.run([sys.executable, str(SCRIPT), "report", "../etc"], cwd=self.repo, capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
