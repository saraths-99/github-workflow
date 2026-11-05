#!/usr/bin/env python3
"""Normalize a raw log attachment into one plain-text file logcat_trim.py can read.

Handles two attachment shapes:
  - A plain .txt/.log file (adb logcat -v threadtime format) -- copied through unchanged.
  - A .zip containing one or more .txt/.log files -- extracted and, if more than one, merged in
    chronological order (by each line's own threadtime timestamp; a line with no timestamp of its
    own, e.g. a stack-trace continuation, stays attached to the timestamped line before it).

Plain Python 3, no AI calls, no network access, no shell-outs (uses the stdlib zipfile module, not
`unzip`). Guards against zip-slip paths and zip bombs. Never prints log content -- only the
resulting file path and a short per-entry manifest (name, size, included/skipped + why), so the
agent calling this script can report what happened without reading raw log text itself.

    python3 logcat_extract.py attachment.zip -o .logs/<ticket-id>/raw/extracted
    python3 logcat_extract.py attachment.txt -o .logs/<ticket-id>/raw/extracted
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".log"}
MAX_TOTAL_BYTES = 200 * 1024 * 1024  # zip-bomb guard

THREADTIME_PREFIX_RE = re.compile(r"^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s")


def timestamp_key(line):
    m = THREADTIME_PREFIX_RE.match(line)
    return line[:18] if m else None


def merge_chronologically(blocks):
    """blocks: one list-of-lines per extracted file, each in its original order."""
    groups = []  # [timestamp_or_None, file_index, group_index, [lines]]
    for file_index, lines in enumerate(blocks):
        current = None
        for line in lines:
            key = timestamp_key(line)
            if key is not None:
                current = [key, file_index, len(groups), [line]]
                groups.append(current)
            elif current is not None:
                current[3].append(line)
            else:
                groups.append([None, file_index, len(groups), [line]])
    groups.sort(key=lambda g: (g[0] is None, g[0] or "", g[1], g[2]))
    merged = []
    for _, _, _, lines in groups:
        merged.extend(lines)
    return merged


def safe_member_path(name):
    norm = Path(name)
    return not norm.is_absolute() and ".." not in norm.parts


def extract_zip(zip_path):
    blocks, manifest, total = [], [], 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not safe_member_path(name):
                manifest.append(f"skipped {name}: unsafe path")
                continue
            if Path(name).suffix.lower() not in TEXT_SUFFIXES:
                manifest.append(f"skipped {name}: not a .txt/.log file")
                continue
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                manifest.append(f"stopped at {name}: extracted size would exceed the {MAX_TOTAL_BYTES} byte cap")
                break
            with zf.open(info) as f:
                text = f.read().decode("utf-8", errors="replace")
            blocks.append(text.splitlines(keepends=True))
            manifest.append(f"included {name} ({info.file_size} bytes)")
    return blocks, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("-o", "--outdir", required=True)
    args = parser.parse_args()

    in_path = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    suffix = in_path.suffix.lower()

    if suffix == ".zip":
        blocks, manifest = extract_zip(in_path)
        if not blocks:
            sys.stderr.write("logcat_extract: no .txt/.log files found in zip\n")
            for line in manifest:
                sys.stderr.write(f"  {line}\n")
            sys.exit(1)
        merged = blocks[0] if len(blocks) == 1 else merge_chronologically(blocks)
        out_path = outdir / "merged.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.writelines(merged)
    elif suffix in TEXT_SUFFIXES:
        text = in_path.read_text(encoding="utf-8", errors="replace")
        out_path = outdir / in_path.name
        out_path.write_text(text, encoding="utf-8")
        manifest = [f"copied {in_path.name} unchanged ({len(text)} chars)"]
    else:
        sys.stderr.write(
            f"logcat_extract: unsupported input type '{suffix or in_path.name}' "
            "(expected .txt, .log or .zip)\n"
        )
        sys.exit(1)

    print(f"# logcat_extract: wrote {out_path}")
    for line in manifest:
        print(f"# {line}")


if __name__ == "__main__":
    main()
