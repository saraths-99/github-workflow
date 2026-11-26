"""Tests for .github/token-tracker/scripts/token_credits.py. Run: python3 -m unittest tests/test_token_credits.py"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "token-tracker" / "scripts" / "token_credits.py"
spec = importlib.util.spec_from_file_location("token_credits", SCRIPT)
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
HEADER = ["Model", "Release status", "Category", "Tier", "Threshold (input tokens)", "Input", "Cached input", "Cache write", "Output"]
ROWS = [
    ["Claude Opus 5.5", "GA", "Powerful", "Default", "Not applicable", 4.0, 0.2, "Not applicable", 20.0],
    ["GPT-6 Luna", "GA", "Lightweight", "Default", "≤ 272K", 0.1, 0.01, 0.125, 0.5],
    ["GPT-6 Luna", "GA", "Lightweight", "Long context", "> 272K", 0.2, 0.02, 0.25, 0.75],
    [("Gemini 3.8 Flash", "1"), "GA", "Fast", "Default", "Not applicable", 0.75, 0.075, 0.9, 3.75],
]


def make_xlsx(path, rows=ROWS, header=HEADER):
    """A minimal .xlsx: shared strings (one rich-text with a footnote run), numbers inline."""
    strings = []

    def sid(text):
        if text not in strings:
            strings.append(text)
        return strings.index(text)

    def cell(ref, v):
        if isinstance(v, float):
            return f'<c r="{ref}"><v>{v}</v></c>'
        return f'<c r="{ref}" t="s"><v>{sid(v)}</v></c>'

    xml_rows = []
    for r, row in enumerate([header] + rows, start=1):
        cells = "".join(cell(f"{chr(65 + i)}{r}", v if not isinstance(v, tuple) else v) for i, v in enumerate(row))
        xml_rows.append(f'<row r="{r}">{cells}</row>')
    sst = ""
    for s in strings:
        if isinstance(s, tuple):
            sst += (f'<si><r><t>{s[0]}</t></r><r><rPr><color rgb="FF1155CC"/><u/></rPr><t>{s[1]}</t></r></si>')
        else:
            sst += f"<si><t>{s}</t></si>"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{MAIN}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Prices" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="x"/></Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{MAIN}">{sst}</sst>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{MAIN}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')


def usage_html(rows):
    body = "".join(f'<tr><td>t</td><td>{a}</td><td>{m}</td><td class="num">{i}</td><td class="num">{o}</td></tr>' for a, m, i, o in rows)
    return ('<html><head><title>Token usage: ABC-1</title></head><body><h2>By agent</h2><table><tr><th>Agent</th></tr><tr><td>x</td></tr></table>'
            '<h2>Every model call</h2><table><thead><tr><th>Time</th><th>Agent</th><th>Model</th><th class="num">Input</th>'
            f'<th class="num">Output</th></tr></thead><tbody>{body}</tbody></table></body></html>')


class Rates(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.xlsx = Path(self.dir.name) / "prices.xlsx"
        make_xlsx(self.xlsx)

    def tearDown(self):
        self.dir.cleanup()

    def test_loads_every_model_and_strips_the_footnote(self):
        rates, problems = tc.load_rates(self.xlsx)
        self.assertEqual(problems, [])
        self.assertEqual(set(rates), {"claude-opus-5.5", "gpt-6-luna", "gemini-3.8-flash"})

    def test_tier_follows_the_calls_input_size(self):
        rates, _ = tc.load_rates(self.xlsx)
        self.assertEqual(tc.pick_rate(rates, "gpt-6-luna", 272_000)["input"], 0.1)
        self.assertEqual(tc.pick_rate(rates, "gpt-6-luna", 272_001)["input"], 0.2)

    def test_date_suffix_is_ignored_but_unknown_models_are_not_guessed(self):
        rates, _ = tc.load_rates(self.xlsx)
        self.assertIsNotNone(tc.pick_rate(rates, "claude-opus-5.5-2026-11-01", 10))
        self.assertIsNone(tc.pick_rate(rates, "gpt-4o-mini-2024-07-18", 10))

    def test_bad_threshold_is_an_error_not_a_guess(self):
        with self.assertRaises(tc.SheetError):
            tc.parse_threshold("about 200K")

    def test_rejects_a_sheet_without_the_price_columns(self):
        make_xlsx(self.xlsx, rows=[["a", "b"]], header=["Name", "Cost"])
        with self.assertRaises(tc.SheetError):
            tc.load_rates(self.xlsx)


class Convert(unittest.TestCase):
    def test_formula_and_unpriced_calls(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            make_xlsx(d / "prices.xlsx")
            (d / "token-usage.html").write_text(usage_html([
                ("dev", "claude-opus-5.5", "1,000,000", "100,000"),
                ("dev", "gpt-6-luna", "300,000", 0),
                ("title", "gpt-4o-mini-2024-07-18", 250, 6),
            ]))
            out = d / "out"
            r = subprocess.run([sys.executable, str(SCRIPT), str(d / "prices.xlsx"), str(d / "token-usage.html"), "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((out / "token-credits.json").read_text())
            self.assertEqual(data["ticketId"], "ABC-1")
            # opus: 1M x $4 + 0.1M x $20 = $6.00; luna over 272K: 0.3M x $0.2 = $0.06; $6.06 at $0.01 a credit
            self.assertAlmostEqual(data["totals"]["usd"], 6.06, places=6)
            self.assertAlmostEqual(data["totals"]["credits"], 606.0, places=4)
            self.assertEqual(data["totals"]["pricedCalls"], 2)
            self.assertEqual([u["model"] for u in data["unpriced"]], ["gpt-4o-mini-2024-07-18"])
            self.assertTrue((out / "token-credits.html").is_file())

    def test_reads_the_trackers_json_too(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "token-usage.json"
            p.write_text(json.dumps({"ticketId": "ABC-2", "calls": [
                {"agentName": "a", "model": "claude-opus-5.5", "inputTokens": 500000, "outputTokens": 0, "timestamp": "t"}]}))
            ticket, calls = tc.read_usage(p)
            self.assertEqual((ticket, calls[0]["input"]), ("ABC-2", 500000))

    def test_html_without_the_call_table_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.html"
            p.write_text("<html><body><table><tr><th>a</th></tr></table></body></html>")
            with self.assertRaises(tc.SheetError):
                tc.read_usage(p)

    def test_agent_names_are_escaped_in_the_page(self):
        s = {"ticketId": "<b>", "totals": {"credits": 0, "pricedCalls": 0, "unpricedCalls": 0, "inputTokens": 0, "outputTokens": 0, "usd": 0.0},
             "byAgent": [{"agent": "<script>", "calls": 1, "inputTokens": 1, "outputTokens": 1, "usd": 0.0, "credits": 0.0, "share": 0.0}],
             "byModel": [], "unpriced": [], "assumptions": [], "calls": []}
        page = tc.render_html(s)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)


if __name__ == "__main__":
    unittest.main()
