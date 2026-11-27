#!/usr/bin/env python3
"""Turns a ticket's token usage into AI credits, using a model price sheet.

    cost in USD = tokens / 1,000,000 x the model's rate per 1M tokens (the sheet's prices are USD)
    AI credits  = cost in USD / 0.01          (1 AI credit = $0.01)

The tracker's `token-usage.html` (or `token-usage.json`) holds every model call with its input and
output tokens. The price sheet is a spreadsheet (.xlsx) with one row per model and tier, and the
columns Model, Threshold (input tokens), Input, Cached input, Cache write and Output. Each call is
priced on its own: input tokens at the model's Input rate, output tokens at its Output rate, and
the two are added, then converted to credits. Where a model has a long-context tier, the row whose threshold covers that call's
input tokens is the one used.

Usage:
    python3 token_credits.py <price sheet.xlsx> <token-usage.html | token-usage.json> [--out DIR]
                             [--usd-per-credit 0.01]

Writes token-credits.html and token-credits.json to --out (default: next to the usage file) and
prints a summary. Standard library only (Python 3.9 or newer); nothing is uploaded.

Things it does not guess:
  - A call whose model has no row in the sheet is left out of the totals and listed as unpriced.
  - The usage file has no cached-token split, so every input token is priced at the full Input
    rate. If part of the input was served from cache, the real figure is lower.
"""
import argparse
import html
import json
import math
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
M = "{%s}" % NS["m"]


class SheetError(Exception):
    pass


# ── Price sheet (.xlsx) ──────────────────────────────────────────────────────────────────────────


def _shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    out = []
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
        runs = si.findall("m:r", NS)
        if runs:
            # A footnote marker (a superscript or underlined run after the name) is not part of the text.
            parts = []
            for r in runs:
                rpr = r.find("m:rPr", NS)
                if rpr is not None and (rpr.find("m:u", NS) is not None or rpr.find("m:vertAlign", NS) is not None):
                    continue
                parts.append(r.findtext("m:t", "", NS))
            out.append("".join(parts).strip())
        else:
            out.append("".join(t.text or "" for t in si.findall("m:t", NS)).strip())
    return out


def _first_sheet_path(z):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheet = wb.find("m:sheets/m:sheet", NS)
    if sheet is None:
        raise SheetError("the workbook has no sheets")
    rid = sheet.get("{%s}id" % NS["r"])
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    for rel in rels.findall("rel:Relationship", NS):
        if rel.get("Id") == rid:
            target = rel.get("Target").lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise SheetError("could not find the first sheet's file in the workbook")


def _col_index(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_rows(path):
    """The first sheet of an .xlsx as a list of rows; each row is a list of str, float or None."""
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        raise SheetError(f"{path} is not a readable .xlsx file ({e})")
    with z:
        shared = _shared_strings(z)
        sheet = ET.fromstring(z.read(_first_sheet_path(z)))
    rows = []
    for row in sheet.findall("m:sheetData/m:row", NS):
        cells = {}
        for c in row.findall("m:c", NS):
            kind, v = c.get("t"), c.find("m:v", NS)
            if kind == "inlineStr":
                value = "".join(t.text or "" for t in c.iter(M + "t")).strip()
            elif v is None or v.text is None:
                value = None
            elif kind == "s":
                value = shared[int(v.text)]
            elif kind in ("str", "e"):
                value = v.text.strip()
            elif kind == "b":
                value = v.text == "1"
            else:
                try:
                    value = float(v.text)
                except ValueError:
                    value = v.text.strip()
            cells[_col_index(c.get("r"))] = value
        if cells:
            rows.append([cells.get(i) for i in range(max(cells) + 1)])
    return rows


def parse_threshold(value):
    """(low, high] of input tokens a price row applies to: 'Not applicable' is every call, '≤ 200K' up to
    200,000, '> 200K' above it. Anything else is an error rather than a guess."""
    t = str(value if value is not None else "").strip().lower().replace(",", "")
    if t in ("", "not applicable", "n/a", "na", "-", "—"):
        return 0.0, math.inf
    m = re.match(r"^(≤|<=|>)\s*([\d.]+)\s*([km]?)$", t)
    if not m:
        raise SheetError(f"can't read the threshold {value!r}; expected 'Not applicable', '≤ 200K' or '> 200K'")
    limit = float(m.group(2)) * {"": 1, "k": 1_000, "m": 1_000_000}[m.group(3)]
    return (0.0, limit) if m.group(1) in ("≤", "<=") else (limit, math.inf)


def norm_model(name):
    return re.sub(r"-+", "-", re.sub(r"[\s_]+", "-", str(name).strip().lower()))


def model_keys(name):
    """The names a model in a usage file may be looked up under: as written, then without a date suffix."""
    n = norm_model(name)
    yield n
    stripped = re.sub(r"-(\d{4}-\d{2}-\d{2}|\d{8})$", "", n)
    if stripped != n:
        yield stripped


def load_rates(path):
    """{normalised model name: [{'label', 'low', 'high', 'input', 'output', 'cached', 'write'}, ...]}"""
    rows = read_rows(path)
    header_at = next((i for i, r in enumerate(rows)
                      if {"model", "input", "output"} <= {str(c).strip().lower() for c in r if c is not None}), None)
    if header_at is None:
        raise SheetError("no header row with Model, Input and Output columns was found in the sheet")
    cols = {}
    for i, c in enumerate(rows[header_at]):
        if c is None:
            continue
        key = str(c).strip().lower()
        if key == "model":
            cols["model"] = i
        elif key.startswith("threshold"):
            cols["threshold"] = i
        elif key in ("input", "cached input", "cache write", "output"):
            cols[key] = i
    rates, current, problems = {}, None, []
    for n, row in enumerate(rows[header_at + 1:], start=header_at + 2):
        def cell(key):
            i = cols.get(key)
            return row[i] if i is not None and i < len(row) else None
        name = cell("model")
        if name not in (None, ""):
            current = str(name).strip()
        if current is None or all(c is None for c in row):
            continue
        inp, out = cell("input"), cell("output")
        if not isinstance(inp, float) or not isinstance(out, float):
            problems.append(f"row {n} ({current}): Input or Output isn't a number, so it was skipped")
            continue
        low, high = parse_threshold(cell("threshold"))
        num = lambda v: v if isinstance(v, float) else None
        rates.setdefault(norm_model(current), []).append({
            "label": current, "low": low, "high": high, "input": inp, "output": out,
            "cached": num(cell("cached input")), "write": num(cell("cache write"))})
    if not rates:
        raise SheetError("the sheet has no priced rows")
    return rates, problems


def pick_rate(rates, model, input_tokens):
    for key in model_keys(model):
        for r in rates.get(key, []):
            if (r["low"] == 0 or input_tokens > r["low"]) and input_tokens <= r["high"]:
                return r
    return None


# ── Usage file (.html or .json) ──────────────────────────────────────────────────────────────────


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._row, self._cell, self.title, self._in_title = [], None, None, "", False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.tables[-1].append(self._row)
            self._row = None
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif self._in_title:
            self.title += data


def _int(text):
    try:
        return int(str(text).replace(",", "").strip())
    except ValueError:
        raise SheetError(f"not a token count: {text!r}")


def read_usage(path):
    """(ticket ID or '', [{'time', 'agent', 'model', 'input', 'output'}]) from token-usage.html or .json."""
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".json":
        data = json.loads(text)
        # The current shape has steps[].calls[] with the input split three ways; the older one has calls[].
        raw = [c for st in data["steps"] for c in st["calls"]] if "steps" in data else data.get("calls", [])
        calls = [{"time": c.get("timestamp", ""), "agent": c.get("agentName", "unknown"), "model": c.get("model", "unknown"),
                  "input": int(c.get("inputTokens") or 0) + int(c.get("cachedInputTokens") or 0) + int(c.get("cacheWriteTokens") or 0),
                  "output": int(c.get("outputTokens") or 0)} for c in raw]
        return data.get("ticketId", ""), calls
    parser = _Tables()
    parser.feed(text)
    for table in parser.tables:
        if table and [h.lower() for h in table[0]] == ["time", "agent", "model", "input", "output"]:
            calls = [{"time": r[0], "agent": r[1], "model": r[2], "input": _int(r[3]), "output": _int(r[4])}
                     for r in table[1:] if len(r) == 5]
            ticket = re.sub(r"^\s*Token usage:\s*", "", parser.title).strip()
            return ticket, calls
    raise SheetError("no 'Every model call' table (Time, Agent, Model, Input, Output) was found in the usage file")


# ── Pricing ──────────────────────────────────────────────────────────────────────────────────────


USD_PER_CREDIT = 0.01


def cost(tokens, rate):
    """USD for `tokens` at `rate` USD per 1M tokens."""
    return tokens / 1_000_000 * rate


def price(calls, rates, usd_per_credit=USD_PER_CREDIT):
    priced, unpriced = [], {}
    for c in calls:
        r = pick_rate(rates, c["model"], c["input"])
        if r is None:
            u = unpriced.setdefault(c["model"], {"model": c["model"], "calls": 0, "inputTokens": 0, "outputTokens": 0,
                                                 "reason": "no row for this model in the sheet"
                                                 if not any(k in rates for k in model_keys(c["model"]))
                                                 else "no row covers this call's input size"})
            u["calls"] += 1
            u["inputTokens"] += c["input"]
            u["outputTokens"] += c["output"]
            continue
        usd = cost(c["input"], r["input"]) + cost(c["output"], r["output"])
        priced.append({**c, "usd": usd, "credits": usd / usd_per_credit, "sheetModel": r["label"],
                       "inputRate": r["input"], "outputRate": r["output"]})
    return priced, sorted(unpriced.values(), key=lambda u: -(u["inputTokens"] + u["outputTokens"]))


def summarise(ticket, priced, unpriced, source_calls, usd_per_credit=USD_PER_CREDIT):
    def group(key):
        g = {}
        for c in priced:
            a = g.setdefault(c[key], {key: c[key], "calls": 0, "inputTokens": 0, "outputTokens": 0, "usd": 0.0, "credits": 0.0})
            a["calls"] += 1
            a["inputTokens"] += c["input"]
            a["outputTokens"] += c["output"]
            a["usd"] += c["usd"]
            a["credits"] += c["credits"]
        return sorted(g.values(), key=lambda a: (-a["credits"], a[key]))

    total = sum(c["credits"] for c in priced)
    by_model = group("model")
    for m in by_model:
        used = sorted({(c["inputRate"], c["outputRate"]) for c in priced if c["model"] == m["model"]})
        m["sheetModel"] = next(c["sheetModel"] for c in priced if c["model"] == m["model"])
        m["rates"] = [{"input": i, "output": o} for i, o in used]
    by_agent = group("agent")
    for g in (by_model, by_agent):
        for a in g:
            a["share"] = a["credits"] / total if total else 0.0
    return {
        "ticketId": ticket,
        "usdPerCredit": usd_per_credit,
        "totals": {"credits": total, "usd": sum(c["usd"] for c in priced), "pricedCalls": len(priced), "unpricedCalls": len(source_calls) - len(priced),
                   "inputTokens": sum(c["input"] for c in priced), "outputTokens": sum(c["output"] for c in priced)},
        "byAgent": by_agent, "byModel": by_model, "unpriced": unpriced,
        "assumptions": [
            f"USD = tokens / 1,000,000 x the sheet's rate per 1M tokens, input and output priced separately and added; credits = USD / {usd_per_credit:g} (1 AI credit = $0.01)",
            "every input token is priced at the full Input rate (the usage file has no cached-token split), so this is an upper bound if any input was cached",
            "calls on a model with no row in the sheet are not in the totals",
        ],
        "calls": [{"time": c["time"], "agent": c["agent"], "model": c["model"], "inputTokens": c["input"],
                   "outputTokens": c["output"], "usd": c["usd"], "credits": c["credits"]} for c in priced],
    }


# ── Output ───────────────────────────────────────────────────────────────────────────────────────


def fmt(x):
    return f"{x:,.2f}"


def usd(x):
    return f"${x:,.4f}"


def render_text(s):
    t, lines = s["totals"], [f"# AI credits — {s['ticketId'] or 'ticket'}", ""]
    lines += [f"- **Total:** {fmt(t['credits'])} credits ({usd(t['usd'])}) across {t['pricedCalls']} priced calls "
              f"({t['inputTokens']:,} input, {t['outputTokens']:,} output tokens)"]
    if t["unpricedCalls"]:
        lines += [f"- **Not priced:** {t['unpricedCalls']} calls, no rate in the sheet (listed below)"]
    lines += ["", "## By model", "", "| Model | Calls | Input tokens | Output tokens | Credits | USD | Share |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {m['model']} | {m['calls']} | {m['inputTokens']:,} | {m['outputTokens']:,} | {fmt(m['credits'])} | {usd(m['usd'])} | {m['share']:.1%} |"
              for m in s["byModel"]]
    lines += ["", "## By agent", "", "| Agent | Calls | Input tokens | Output tokens | Credits | USD | Share |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {a['agent']} | {a['calls']} | {a['inputTokens']:,} | {a['outputTokens']:,} | {fmt(a['credits'])} | {usd(a['usd'])} | {a['share']:.1%} |"
              for a in s["byAgent"]]
    if s["unpriced"]:
        lines += ["", "## Not priced", "", "| Model | Calls | Input tokens | Output tokens | Why |", "|---|---|---|---|---|"]
        lines += [f"| {u['model']} | {u['calls']} | {u['inputTokens']:,} | {u['outputTokens']:,} | {u['reason']} |" for u in s["unpriced"]]
    return "\n".join(lines + ["", "Assumptions: " + "; ".join(s["assumptions"]) + "."])


CSS = """
:root { --bg:#f7f7f5; --surface:#fff; --text:#1f1f1d; --muted:#6b6a65; --border:#e4e3de; --accent:#4b5bd6; --accent-soft:#e3e6fb; }
@media (prefers-color-scheme: dark) { :root { --bg:#1b1b1a; --surface:#252523; --text:#ecebe6; --muted:#a3a29b; --border:#3a3936; --accent:#8c98f0; --accent-soft:#2f3359; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:980px; margin:0 auto; padding:32px 16px 48px; }
.eyebrow { margin:0; color:var(--muted); font-size:13px; }
h1 { margin:2px 0 4px; font-size:28px; font-weight:600; }
h2 { margin:32px 0 10px; font-size:17px; font-weight:600; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin-top:24px; }
.tile, .card { background:var(--surface); border:1px solid var(--border); border-radius:10px; }
.tile { padding:14px 16px; } .tile .label { color:var(--muted); font-size:13px; }
.tile .value { font-size:26px; font-weight:600; font-variant-numeric:tabular-nums; }
.card { overflow-x:auto; } table { width:100%; border-collapse:collapse; font-size:14px; }
th, td { padding:9px 14px; text-align:left; border-bottom:1px solid var(--border); white-space:nowrap; }
th { color:var(--muted); font-weight:500; font-size:13px; } tr:last-child td { border-bottom:none; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.share { display:flex; align-items:center; gap:10px; min-width:170px; }
.bar { flex:1; height:8px; background:var(--accent-soft); border-radius:4px; overflow:hidden; }
.bar span { display:block; height:100%; background:var(--accent); }
.pct { width:56px; text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }
footer, .note { margin-top:20px; color:var(--muted); font-size:13px; }
@media (max-width:600px) { .bar { display:none; } .share { min-width:0; } }
"""


def render_html(s):
    e, t = html.escape, s["totals"]

    def share(x):
        return f'<div class="share"><div class="bar"><span style="width:{x * 100:.1f}%"></span></div><span class="pct">{x:.1%}</span></div>'

    def table(heads, rows, nums):
        th = "".join(f'<th class="num">{h}</th>' if i in nums else f"<th>{h}</th>" for i, h in enumerate(heads))
        body = "".join("<tr>" + "".join(f'<td class="num">{c}</td>' if i in nums else f"<td>{c}</td>"
                                         for i, c in enumerate(r)) + "</tr>" for r in rows)
        return f'<div class="card"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'

    def block(items, key):
        return table([key.title(), "Share of credits", "Calls", "Input", "Output", "Credits", "USD"],
                     [(e(a[key]), share(a["share"]), a["calls"], f"{a['inputTokens']:,}", f"{a['outputTokens']:,}", fmt(a["credits"]), usd(a["usd"]))
                      for a in items], {2, 3, 4, 5, 6})

    parts = [f'<p class="eyebrow">AI credits</p><h1>{e(s["ticketId"] or "Ticket")}</h1>',
             '<section class="tiles">'
             f'<div class="tile"><div class="label">Total credits</div><div class="value">{fmt(t["credits"])}</div></div>'
             f'<div class="tile"><div class="label">Total USD</div><div class="value">{usd(t["usd"])}</div></div>'
             f'<div class="tile"><div class="label">Priced calls</div><div class="value">{t["pricedCalls"]:,}</div></div>'
             f'<div class="tile"><div class="label">Not priced</div><div class="value">{t["unpricedCalls"]:,}</div></div>'
             f'<div class="tile"><div class="label">Tokens priced</div><div class="value">{t["inputTokens"] + t["outputTokens"]:,}</div></div></section>',
             "<h2>By model</h2>", table(["Model", "Share of credits", "Calls", "Input", "Output", "Credits", "USD", "Rate in / out (USD per 1M)"],
                                        [(e(m["model"]), share(m["share"]), m["calls"], f"{m['inputTokens']:,}", f"{m['outputTokens']:,}",
                                          fmt(m["credits"]), usd(m["usd"]), " · ".join(f"{r['input']:g} / {r['output']:g}" for r in m["rates"]))
                                         for m in s["byModel"]], {2, 3, 4, 5, 6, 7}),
             "<h2>By agent</h2>", block(s["byAgent"], "agent")]
    if s["unpriced"]:
        parts += ["<h2>Not priced</h2>", table(["Model", "Calls", "Input", "Output", "Why"],
                                              [(e(u["model"]), u["calls"], f"{u['inputTokens']:,}", f"{u['outputTokens']:,}", e(u["reason"]))
                                               for u in s["unpriced"]], {1, 2, 3})]
    parts += ["<h2>Every priced call</h2>", table(["Time", "Agent", "Model", "Input", "Output", "Credits"],
                                                   [(e(c["time"]), e(c["agent"]), e(c["model"]), f"{c['inputTokens']:,}",
                                                     f"{c['outputTokens']:,}", f"{c['credits']:.4f}") for c in s["calls"]], {3, 4, 5}),
              '<p class="note">' + e("; ".join(s["assumptions"])) + ".</p>"]
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>AI credits: {e(s["ticketId"] or "ticket")}</title><style>{CSS}</style></head><body><main>' + "".join(parts) +
            "</main></body></html>")


def main(argv=None):
    p = argparse.ArgumentParser(description="Convert a ticket's token usage into AI credits using a model price sheet.")
    p.add_argument("pricing", help="price sheet (.xlsx): Model, Threshold (input tokens), Input, Cached input, Cache write, Output")
    p.add_argument("usage", help="the tracker's token-usage.html or token-usage.json")
    p.add_argument("--out", help="folder for token-credits.html and .json (default: next to the usage file)")
    p.add_argument("--usd-per-credit", type=float, default=USD_PER_CREDIT,
                   help="USD value of one AI credit (default 0.01, GitHub's rate)")
    args = p.parse_args(argv)
    try:
        rates, problems = load_rates(args.pricing)
        ticket, calls = read_usage(args.usage)
    except (SheetError, OSError, ValueError, KeyError, ET.ParseError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not calls:
        print("error: the usage file has no model calls", file=sys.stderr)
        return 1
    if args.usd_per_credit <= 0:
        print("error: --usd-per-credit must be above zero", file=sys.stderr)
        return 1
    priced, unpriced = price(calls, rates, args.usd_per_credit)
    summary = summarise(ticket, priced, unpriced, calls, args.usd_per_credit)
    out = Path(args.out) if args.out else Path(args.usage).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "token-credits.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "token-credits.html").write_text(render_html(summary), encoding="utf-8")
    for note in problems:
        print(f"warning: {note}", file=sys.stderr)
    print(render_text(summary))
    print(f"\nWritten to {out}: token-credits.html, token-credits.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
