#!/usr/bin/env python3
"""Group a trimmed log's warnings and errors by signature.

Plain Python 3, no AI calls. Input is the output of logcat_trim.py (threadtime lines, optionally
with a trailing " (xN)" repeat count, plus its leading "# " header lines, which are ignored here).

    python3 logcat_digest.py trimmed.log -o digest.md
"""
import argparse
import re
import sys
from collections import OrderedDict

LINE_RE = re.compile(
    r"^(?P<date>\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>[VDIWEF])\s+(?P<tag>[^:]*):\s?"
    r"(?P<msg>.*?)(?:\s\(x(?P<repeat>\d+)\))?$"
)

NORMALIZE_PATTERNS = [
    (re.compile(r"0x[0-9a-fA-F]+"), "0xHEX"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}\b"), "UUID"),
    (re.compile(r"\d+"), "N"),
]


def normalize_message(msg):
    for pattern, placeholder in NORMALIZE_PATTERNS:
        msg = pattern.sub(placeholder, msg)
    return msg.strip()


def digest(lines):
    groups = OrderedDict()
    for raw in lines:
        if raw.startswith("#") or not raw.strip():
            continue
        m = LINE_RE.match(raw.rstrip("\n"))
        if not m:
            continue
        level = m.group("level")
        if level not in ("W", "E"):
            continue
        tag = m.group("tag").strip()
        signature = normalize_message(m.group("msg"))
        count = int(m.group("repeat") or 1)
        timestamp = f"{m.group('date')} {m.group('time')}"

        key = (level, tag, signature)
        if key not in groups:
            groups[key] = {"count": 0, "first": timestamp, "last": timestamp}
        g = groups[key]
        g["count"] += count
        if timestamp < g["first"]:
            g["first"] = timestamp
        if timestamp > g["last"]:
            g["last"] = timestamp

    return sorted(groups.items(), key=lambda kv: kv[1]["first"])


def render_markdown(rows):
    out = [
        "| Level | Tag | Signature | Count | First | Last |",
        "|---|---|---|---|---|---|",
    ]
    for (level, tag, signature), g in rows:
        out.append(
            f"| {level} | {tag} | {signature} | {g['count']} | {g['first']} | {g['last']} |"
        )
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    rows = digest(lines)
    output = render_markdown(rows)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
