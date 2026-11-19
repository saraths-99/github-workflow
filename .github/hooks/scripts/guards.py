#!/usr/bin/env python3
"""The four Copilot guard hooks, in Copilot's native hook format (see hook-protocol.md).

Usage: guards.py <protect-secrets|block-force-push|guard-context-docs|format-kotlin>, with the
hook's JSON payload on stdin. Accepts both payload shapes: VS Code's (tool_name / tool_input) and
the Copilot CLI's (toolName / toolArgs). Prints nothing to let a call through, so the IDE's own
confirmation still applies; prints one decision object to deny or ask.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
SENSITIVE_FILE = HOOKS_DIR / "sensitive-paths.txt"
CONTEXT_DOCS = {"project-context.md", "architecture.md"}
# The only commands allowed to name a raw log: the log analyser's own extract and trim scripts.
RAW_LOG_SCRIPTS = re.compile(r"^\s*python3?\s+\S*\.github/log-analyser/scripts/logcat_(extract|trim)\.py\b")
# Where a downloaded ticket attachment may be written: one file directly under a ticket's raw/ folder.
RAW_DOWNLOAD_TARGET = re.compile(r"^(?:\./)?\.logs/[^/\s]+/raw/[^/\s]+$")
CURL_FLAGS = re.compile(r"^-[fsSL]+$|^--(?:location|silent|show-error|fail|create-dirs)$")
CURL_VALUE_FLAGS = {"--retry", "--max-time", "--connect-timeout"}
EDIT_TOOL = re.compile(r"(?i)(edit|replace|create|write|patch|insert|delete|rename|move)")
POSTING_TOOL = re.compile(r"(?i)(comment|pull.?request|issue|confluence|page|description)")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.M)


def read_call():
    data = json.load(sys.stdin)
    tool = data.get("tool_name") or data.get("toolName") or ""
    args = data.get("tool_input", data.get("toolArgs"))
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            args = {"input": args}
    paths, texts, command = [], [], ""

    def walk(value, key=""):
        nonlocal command
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, k)
        elif isinstance(value, list):
            for v in value:
                walk(v, key)
        elif isinstance(value, str):
            if key == "command":
                command = value
            elif re.search(r"(?i)(path|file|uri|dir)", key):
                paths.append(value.removeprefix("file://"))
            else:
                texts.append(value)
                paths.extend(PATCH_FILE.findall(value))

    walk(args)
    return {"tool": tool, "paths": paths, "command": command, "text": "\n".join(texts)}


def decide(decision, reason):
    # Top-level fields for the Copilot CLI, hookSpecificOutput for VS Code.
    print(json.dumps({
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }))
    sys.exit(0)


def sensitive_patterns():
    try:
        lines = SENSITIVE_FILE.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def is_sensitive(path, patterns):
    path = path.replace("\\", "/")
    candidates = {path, path.rstrip("/") + "/"}
    return any(fnmatch.fnmatch(c, p) or fnmatch.fnmatch(c, "*/" + p) for c in candidates for p in patterns)


def is_raw_download_target(path):
    return bool(RAW_DOWNLOAD_TARGET.match(path)) and ".." not in path.split("/")


def is_attachment_download(command):
    """True only for the `curl` downloadJiraIssueAttachment hands back: one https URL, saved to one file
    directly under .logs/<ticket>/raw/. Anything else (extra flags, a second target, chaining, a body to
    upload) isn't, so it falls through to the normal raw-log rule and is denied."""
    if re.search(r"[`\n]|\$\(", command):
        return False
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return False
    if not words or words[0] != "curl" or any(re.fullmatch(r"[;&|()<>]+", w) for w in words):
        return False
    target, urls, i = None, [], 1
    while i < len(words):
        word = words[i]
        if word in ("-o", "--output") and i + 1 < len(words) and target is None:
            target, i = words[i + 1], i + 2
        elif word in ("-H", "--header") and i + 1 < len(words) and not words[i + 1].startswith("@"):
            i += 2
        elif word in CURL_VALUE_FLAGS and i + 1 < len(words) and words[i + 1].isdigit():
            i += 2
        elif CURL_FLAGS.match(word):
            i += 1
        elif word.startswith("https://"):
            urls.append(word)
            i += 1
        else:
            return False
    return target is not None and is_raw_download_target(target) and len(urls) == 1


def protect_secrets(call):
    patterns = sensitive_patterns()
    # downloadJiraIssueAttachment only builds the download command; it writes nothing itself.
    download_call = "downloadJiraIssueAttachment" in call["text"]
    for p in call["paths"]:
        if is_sensitive(p, patterns) and not (download_call and is_raw_download_target(p)):
            decide("deny", f"{p} matches a sensitive-paths.txt entry, so Copilot can't touch it")
    command = call["command"]
    chained = re.search(r"[;&|`\n]|\$\(", command)
    if command and not is_attachment_download(command) and (chained or not RAW_LOG_SCRIPTS.match(command)):
        try:
            words = shlex.split(command)
        except ValueError:
            words = command.split()
        for word in words:
            if is_sensitive(word, patterns):
                decide("deny", f"the command names {word}, which matches a sensitive-paths.txt entry")
    text = call["text"]
    if text and POSTING_TOOL.search(call["tool"]):
        jwt_re = re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
        token_re = re.compile(r"(?i)\b(token|auth(?:orization)?|bearer|api[_-]?key|secret)\b\s*[=:]\s*\S+")
        if jwt_re.search(text) or token_re.search(text):
            decide("deny", "the text looks like it contains a JWT or a token")


def block_force_push(call):
    command = call["command"]
    if re.search(r"\bgit\b.*\bpush\b", command) and re.search(
        r"(--force\b|--force-with-lease\b|(?<!\S)-f(?!\S))", command
    ):
        decide("deny", "git push --force (or -f / --force-with-lease) is blocked")


def guard_context_docs(call):
    edits = EDIT_TOOL.search(call["tool"]) and any(
        os.path.basename(p) in CONTEXT_DOCS for p in call["paths"]
    )
    if edits or any(name in call["command"] for name in CONTEXT_DOCS):
        decide("ask", "this touches project-context.md or architecture.md, which only change on purpose")


def format_kotlin(call):
    if not any(p.endswith((".kt", ".kts")) for p in call["paths"]):
        return
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    repo = Path(root.stdout.strip() or ".")
    if not os.access(repo / "gradlew", os.X_OK):
        return
    for task in ("ktlintFormat", "spotlessApply"):
        done = subprocess.run(["./gradlew", task, "-q"], cwd=repo, capture_output=True)
        if done.returncode == 0:
            return


GUARDS = {
    "protect-secrets": protect_secrets,
    "block-force-push": block_force_push,
    "guard-context-docs": guard_context_docs,
    "format-kotlin": format_kotlin,
}

if __name__ == "__main__":
    GUARDS[sys.argv[1]](read_call())
