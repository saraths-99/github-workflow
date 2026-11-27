#!/usr/bin/env python3
"""Pull back the context a trimmed log leaves out, as one small redacted report.

logcat_trim.py keeps only the app's own process, a window around the issue time, and drops noisy
Bluetooth tags unless they are errors; logcat_digest.py then keeps only warnings and errors. That is
right for finding the errors and wrong for explaining them: the stack's connection states, the
process dying or restarting, the lead-up before the window, whether the same error was already
happening an hour earlier, and the app, phone and firmware versions are all outside what it shows.
This reads the full extracted log again and returns just those things, capped, redacted the same way.

Plain Python 3, no AI calls, no network access:

    python3 logcat_context.py extracted.log --package com.example.app --at "16:51:43" \\
        --tag BtGatt.GattService --tag BleCommandQueue --grep "status=133" -o context.md

Sections, always in this order:
  Log boundaries     first and last line, the app's PIDs, the line nearest the issue time, gaps
  Environment        version, device, firmware and Bluetooth-state lines (best effort)
  Process lifecycle  app start, death, kill, crash and ANR lines, and Bluetooth restarts, any process
  Lead-up            every level, every process, noise tags included, in the window around --at,
                     for the given --tag/--grep (default: all warnings and errors of any process)
  How often          per-minute counts over the whole log for each --tag/--grep, and for app errors,
                     so a chronic error can be told from one that began at the issue time

Environment and lifecycle matching is by fixed patterns; finding nothing there is not proof the log
holds nothing. Output is capped by --max-lines per section, keeping the lines nearest --at.
"""
import argparse
import re
import sys
from collections import Counter

import logcat_trim as lt

ENV_PATTERNS = re.compile(
    r"(?i)\b(versionName|versionCode|app version|build\.(model|manufacturer|version|fingerprint)|"
    r"ro\.build|manufacturer|android (version|\d+)|sdk_int|firmware|fw[ _-]?version|"
    r"hardware version|bootloader|mtu|bond(ed|ing)? state|bluetoothadapter.*state|"
    r"permission.*(granted|denied)|battery.*(optimi|saver)|doze|power save)\b"
)
LIFECYCLE_COMMON = re.compile(
    r"(?i)(am_proc_died|am_kill|am_crash|am_anr|ANR in |FATAL EXCEPTION|Force stopping|"
    r"lmkd|Out of memory|OutOfMemoryError|BluetoothManagerService.*(state|crash|died|restart)|"
    r"bluetooth.*(has died|crash|restart))"
)
MAX_LINE = 300


def parse(raw_lines, counts):
    entries, unparsed = [], 0
    for raw in raw_lines:
        line = lt.redact_line(raw.rstrip("\n"), counts)
        m = lt.THREADTIME_RE.match(line)
        if not m:
            unparsed += 1
            continue
        gd = m.groupdict()
        tag, msg = lt.tag_and_msg(gd)
        entries.append({"date": gd["date"], "time": gd["time"], "pid": gd["pid"], "tid": gd["tid"],
                        "level": gd["level"], "tag": tag.strip(), "msg": msg})
    return entries, unparsed


def fmt(e, app_pids):
    mark = "?" if app_pids is None else ("A" if e["pid"] in app_pids else "S")
    text = f"{mark} {e['date']} {e['time']} {e['pid']} {e['tid']} {e['level']} {e['tag']}: {e['msg']}"
    return text if len(text) <= MAX_LINE else text[:MAX_LINE] + " ..."


def distance(e, at_secs):
    if at_secs is None:
        return 0
    s = lt.line_seconds(e)
    return min(abs(s - at_secs), abs(s - at_secs - 86400), abs(s - at_secs + 86400))


def keep_nearest(entries, at_secs, limit):
    """At most `limit` entries, those nearest the issue time, back in log order. Also returns how many were cut."""
    if len(entries) <= limit:
        return entries, 0
    chosen = sorted(range(len(entries)), key=lambda i: distance(entries[i], at_secs))[:limit]
    return [entries[i] for i in sorted(chosen)], len(entries) - limit


def section_boundaries(entries, unparsed, app_pids, at_secs, gap):
    out = ["## Log boundaries"]
    if not entries:
        return out + ["No readable log lines."]
    first, last = entries[0], entries[-1]
    out.append(f"- First line: {first['date']} {first['time']} · last line: {last['date']} {last['time']}")
    out.append(f"- Lines read: {len(entries):,} ({unparsed:,} unreadable) · processes seen: "
               f"{len({e['pid'] for e in entries})}")
    out.append("- App process(es): " + (", ".join(sorted(app_pids)) if app_pids else "not found (no `Start proc` line for the package)"))
    if at_secs is not None:
        nearest = min(entries, key=lambda e: distance(e, at_secs))
        out.append(f"- Line nearest the issue time: {nearest['date']} {nearest['time']} "
                   f"({distance(nearest, at_secs)} s away)")
    gaps = []
    for a, b in zip(entries, entries[1:]):
        delta = (lt.line_seconds(b) - lt.line_seconds(a)) % 86400
        if gap <= delta < 43200:
            gaps.append((a, b, delta))
    for a, b, delta in gaps[:10]:
        out.append(f"- Gap of {delta} s between {a['date']} {a['time']} and {b['date']} {b['time']}: "
                   f"nothing was logged, or the capture lost it")
    if len(gaps) > 10:
        out.append(f"- {len(gaps) - 10} more gaps not shown")
    return out


def section_environment(entries, app_pids, limit):
    seen, hits = set(), []
    for e in entries:
        text = f"{e['tag']}: {e['msg']}"
        if ENV_PATTERNS.search(text) and text not in seen:
            seen.add(text)
            hits.append(e)
    shown, cut = hits[:limit], max(len(hits) - limit, 0)
    out = ["## Environment (best effort: absence is not proof)"]
    out += [fmt(e, app_pids) for e in shown] or ["Nothing matched the version, device, firmware or Bluetooth-state patterns."]
    if cut:
        out.append(f"... {cut} more distinct lines not shown")
    return out


def section_lifecycle(entries, package, app_pids, limit):
    pats = [LIFECYCLE_COMMON]
    if package:
        p = re.escape(package)
        pats.append(re.compile(rf"(Start proc \d+:{p}|Process {p}.*(has died|died)|Killing .*{p}|"
                               rf"Force stopping {p}|{p}.*(crash|ANR))"))
    hits = [e for e in entries if any(p.search(f"{e['tag']}: {e['msg']}") for p in pats)]
    shown, cut = hits[:limit], max(len(hits) - limit, 0)
    out = ["## Process lifecycle (any process)"]
    out += [fmt(e, app_pids) for e in shown] or ["No start, death, kill, crash, ANR or Bluetooth-restart lines found."]
    if cut:
        out.append(f"... {cut} more lines not shown")
    return out


def matcher(tags, greps):
    tag_set = {t.strip() for t in tags}
    patterns = [re.compile(g) for g in greps]
    return lambda e: e["tag"] in tag_set or any(p.search(e["msg"]) for p in patterns)


def section_leadup(entries, tags, greps, at_secs, lead, tail, app_pids, limit):
    out = [f"## Lead-up and aftermath ({lead} s before to {tail} s after the issue time; every level, every process)"]
    if at_secs is None:
        return out + ["No --at given, so no window."]
    window = [e for e in entries if lt.in_window(e, at_secs, lead, tail)]
    if tags or greps:
        wanted = matcher(tags, greps)
        picked = [e for e in window if wanted(e)]
        out.append(f"Selected by tag/pattern: {', '.join(list(tags) + list(greps))}")
    else:
        picked = [e for e in window if e["level"] in ("W", "E", "F")]
        out.append("No --tag or --grep given: every warning and error from any process in the window.")
    shown, cut = keep_nearest(picked, at_secs, limit)
    out += [fmt(e, app_pids) for e in shown] or ["Nothing matched in the window."]
    if cut:
        out.append(f"... {cut} more lines not shown (the {limit} nearest the issue time were kept)")
    return out


def minute_key(e):
    return f"{e['date']} {e['time'][:5]}"


def histogram(title, selected, at_secs, rows=12, near_min=5):
    out = [f"### {title}"]
    if not selected:
        return out + ["Never seen in the log."]
    per_min = Counter(minute_key(e) for e in selected)
    near = {}
    if at_secs is not None:
        for e in selected:
            if distance(e, at_secs) <= near_min * 60:
                near[minute_key(e)] = per_min[minute_key(e)]
    top = dict(per_min.most_common(rows))
    keys = sorted({**top, **near})
    out.append(f"- {len(selected):,} lines, first {minute_key(selected[0])}, last {minute_key(selected[-1])}, "
               f"in {len(per_min)} different minutes")
    out += [f"  {k}  {per_min[k]:,}" for k in keys]
    if len(per_min) > len(keys):
        out.append(f"  ... {len(per_min) - len(keys)} other minutes with fewer lines")
    return out


def section_frequency(entries, tags, greps, app_pids, at_secs):
    out = ["## How often (per minute, whole log; busiest minutes and those within 5 minutes of the issue)"]
    for tag in tags:
        out += histogram(f"Tag {tag}", [e for e in entries if e["tag"] == tag.strip()], at_secs)
    for g in greps:
        p = re.compile(g)
        out += histogram(f"Pattern {g}", [e for e in entries if p.search(e["msg"])], at_secs)
    app_errors = [e for e in entries if e["level"] in ("E", "F") and (app_pids is None or e["pid"] in app_pids)]
    out += histogram("Errors from the app process", app_errors, at_secs)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="the extracted raw log (output of logcat_extract.py)")
    parser.add_argument("--package", help="app package id, used to resolve its PID(s)")
    parser.add_argument("--pid", help="explicit PID; overrides --package resolution")
    parser.add_argument("--at", help="issue time, HH:MM:SS")
    parser.add_argument("--lead", type=int, default=300, help="seconds before --at for the lead-up (default 300)")
    parser.add_argument("--tail", type=int, default=60, help="seconds after --at (default 60)")
    parser.add_argument("--tag", action="append", default=[], help="a tag to follow in every process; repeatable")
    parser.add_argument("--grep", action="append", default=[], help="a regex on the message to follow; repeatable")
    parser.add_argument("--gap", type=int, default=60, help="report gaps of at least this many seconds (default 60)")
    parser.add_argument("--max-lines", type=int, default=150, help="cap per section (default 150)")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()
    counts = {"JWT": 0, "EMAIL": 0, "TOKEN": 0}
    entries, unparsed = parse(raw_lines, counts)
    app_pids = lt.resolve_pids([f"{e['tag']}: {e['msg']}" for e in entries], args.package, args.pid)
    at_secs = None
    if args.at:
        t = lt.parse_at_time(args.at)
        at_secs = t.hour * 3600 + t.minute * 60 + t.second

    parts = [
        [f"# logcat_context: {len(entries):,} lines read from {args.input}",
         f"# redacted: {counts['TOKEN']} tokens, {counts['JWT']} JWTs, {counts['EMAIL']} emails",
         "# A = the app's process, S = another process, ? = the app's process is unknown"],
        section_boundaries(entries, unparsed, app_pids, at_secs, args.gap),
        section_environment(entries, app_pids, args.max_lines),
        section_lifecycle(entries, args.package, app_pids, args.max_lines),
        section_leadup(entries, args.tag, args.grep, at_secs, args.lead, args.tail, app_pids, args.max_lines),
        section_frequency(entries, args.tag, args.grep, app_pids, at_secs),
    ]
    output = "\n\n".join("\n".join(p) for p in parts) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
