#!/usr/bin/env python3
"""Redact, then keep only the app's process and a window around the issue time.

Plain Python 3, no AI calls, no network access. Testers can run this directly:

    python3 logcat_trim.py logcat.txt --package com.example.app --at "16:51:43" -o trimmed.log

Input is accepted in either of two header shapes (both starting `MM-DD HH:MM:SS.mmm`):
  - `adb logcat -v threadtime`: `MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message` (colon-separated
    tag, exactly two numeric fields before LEVEL).
  - The app's own in-app log export: `MM-DD HH:MM:SS.mmm PID TID <extra numeric field(s)> LEVEL
    TAG<padding>message` (no colon; TAG is a fixed-width, space-padded column, truncated with
    "..." if the real tag is too long to fit, and may be blank).
Which shape a given line uses is detected line-by-line from whether a colon immediately follows
the tag token (classic) or two-or-more spaces do (app export) -- a single file can't mix an
`adb logcat` capture with an app-exported one, but this keeps either working without a flag.
"""
import argparse
import re
import sys
from datetime import time as dtime

THREADTIME_RE = re.compile(
    r"^(?P<date>\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)(?:\s+\d+)*\s+(?P<level>[VDIWEF])\s"
    r"(?:(?P<tag_colon>[^\s:]*):\s?(?P<msg_colon>.*)"
    r"|(?P<tag_padded>\S*)\s{2,}(?P<msg_padded>.*)"
    r"|(?P<tag_single>\S*)\s+(?P<msg_single>.*)"
    r"|(?P<tag_bare>\S*))$"
)
_TAG_GROUPS = ("tag_colon", "tag_padded", "tag_single", "tag_bare")
_MSG_GROUPS = ("msg_colon", "msg_padded", "msg_single")


def tag_and_msg(groupdict):
    tag = next((groupdict[k] for k in _TAG_GROUPS if groupdict.get(k) is not None), "")
    msg = next((groupdict[k] for k in _MSG_GROUPS if groupdict.get(k) is not None), "")
    return tag, msg
START_PROC_RE = re.compile(r"Start proc\s+(\d+):([^/\s]+)/")

JWT_RE = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TOKEN_KV_RE = re.compile(
    r"(?i)\b(token|auth(?:orization)?|bearer|api[_-]?key|secret)\b\s*[=:]\s*\S+"
)

DEFAULT_NOISE_TAGS = frozenset(
    {"BluetoothLeScanner", "bt_btm", "BtGatt.ContextMap", "BtGatt.GattService"}
)


def redact_line(line, counts):
    def _sub(pattern, label, text):
        def repl(m):
            counts[label] += 1
            return f"[REDACTED_{label}]"

        return pattern.sub(repl, text)

    line = _sub(JWT_RE, "JWT", line)
    line = _sub(EMAIL_RE, "EMAIL", line)
    line = _sub(TOKEN_KV_RE, "TOKEN", line)
    return line


def resolve_pids(lines, package, explicit_pid):
    if explicit_pid is not None:
        return {explicit_pid}
    if package is None:
        return None
    pids = set()
    for line in lines:
        m = START_PROC_RE.search(line)
        if not m:
            continue
        pid, proc = m.group(1), m.group(2)
        proc_pkg = proc.split(":", 1)[0]
        if proc_pkg == package:
            pids.add(pid)
    return pids or None


def parse_at_time(value):
    h, m, s = (int(x) for x in value.split(":"))
    return dtime(h, m, s)


def line_seconds(entry):
    h, m, s_ms = entry["time"].split(":")
    s = s_ms.split(".", 1)[0]
    return int(h) * 3600 + int(m) * 60 + int(s)


def in_window(entry, at_secs, before, after):
    if at_secs is None:
        return True
    secs = line_seconds(entry)
    window_start, window_end = at_secs - before, at_secs + after
    for candidate in (secs, secs - 86400, secs + 86400):
        if window_start <= candidate <= window_end:
            return True
    return False


def load_noise_tags(path, extra):
    tags = set(DEFAULT_NOISE_TAGS)
    tags.update(extra or [])
    if path:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                tag = raw.strip()
                if tag and not tag.startswith("#"):
                    tags.add(tag)
    return tags


def fold_repeats(entries):
    folded = []
    for entry in entries:
        if folded:
            last = folded[-1]
            if (last["tag"], last["msg"]) == (entry["tag"], entry["msg"]):
                last["count"] += 1
                continue
        entry["count"] = 1
        folded.append(entry)
    return folded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--package", help="app package id, used to resolve its PID(s)")
    parser.add_argument("--pid", help="explicit PID; overrides --package resolution")
    parser.add_argument("--at", help="issue time, HH:MM:SS; omit to skip the time window")
    parser.add_argument("--before", type=int, default=120, help="seconds before --at to keep")
    parser.add_argument("--after", type=int, default=30, help="seconds after --at to keep")
    parser.add_argument("--noise-tags-file", help="extra noise tags, one per line")
    parser.add_argument("--extra-noise-tag", action="append", default=[])
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8", errors="replace") as f:
        raw_lines = f.readlines()

    redact_counts = {"JWT": 0, "EMAIL": 0, "TOKEN": 0}
    redacted_lines = [redact_line(line.rstrip("\n"), redact_counts) for line in raw_lines]

    pids = resolve_pids(redacted_lines, args.package, args.pid)
    pid_warning = None
    if args.package and pids is None:
        pid_warning = f"no process found for package '{args.package}'; process filter skipped"

    at_secs = None
    if args.at:
        t = parse_at_time(args.at)
        at_secs = t.hour * 3600 + t.minute * 60 + t.second
    else:
        pid_warning = (pid_warning or "") + (
            "; " if pid_warning else ""
        ) + "no --at given; time window skipped"

    entries = []
    for line in redacted_lines:
        m = THREADTIME_RE.match(line)
        if not m:
            continue
        gd = m.groupdict()
        tag, msg = tag_and_msg(gd)
        entries.append({
            "date": gd["date"], "time": gd["time"], "pid": gd["pid"], "tid": gd["tid"],
            "level": gd["level"], "tag": tag, "msg": msg,
        })

    before_count = len(entries)

    if pids is not None:
        entries = [e for e in entries if e["pid"] in pids]
    after_process_count = len(entries)

    entries = [e for e in entries if in_window(e, at_secs, args.before, args.after)]
    after_window_count = len(entries)

    noise_tags = load_noise_tags(args.noise_tags_file, args.extra_noise_tag)
    entries = [
        e for e in entries if e["level"] == "E" or e["tag"].strip() not in noise_tags
    ]
    after_noise_count = len(entries)

    entries = fold_repeats(entries)
    after_fold_count = len(entries)

    header = [
        f"# logcat_trim: {before_count} lines -> {after_window_count} lines "
        f"(process+window) -> {after_noise_count} lines (noise tags dropped) "
        f"-> {after_fold_count} lines (repeats folded)",
        f"# redacted: {redact_counts['TOKEN']} tokens, {redact_counts['JWT']} JWTs, "
        f"{redact_counts['EMAIL']} emails",
    ]
    if pid_warning:
        header.append(f"# warning: {pid_warning}")

    out_lines = []
    for e in entries:
        suffix = f" (x{e['count']})" if e["count"] > 1 else ""
        out_lines.append(
            f"{e['date']} {e['time']} {e['pid']} {e['tid']} {e['level']} "
            f"{e['tag']}: {e['msg']}{suffix}"
        )

    output = "\n".join(header + out_lines) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
