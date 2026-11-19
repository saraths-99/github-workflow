"""Tests for the raw-log rule in .github/hooks/scripts/guards.py. Run: python3 -m unittest tests/test_guards.py"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "hooks" / "scripts" / "guards.py"
URL = "https://api.media.atlassian.com/file/abc/binary?token=x&client=y"


def decision(tool_name, tool_input):
    """The guard's decision for a call: 'deny', 'ask', or None when it prints nothing and lets it through."""
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "protect-secrets"],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["permissionDecision"] if out.strip() else None


def run(command):
    return decision("run_in_terminal", {"command": command})


class AttachmentDownload(unittest.TestCase):
    def test_curl_into_raw_folder_is_allowed(self):
        self.assertIsNone(run(f"curl -fsSL -o .logs/HALOM-1/raw/log.zip '{URL}'"))
        self.assertIsNone(run(f'curl -L --output ./.logs/HALOM-1/raw/log.txt "{URL}"'))

    def test_other_ways_into_raw_are_denied(self):
        for command in [
            f"curl -fsSL -o .logs/HALOM-1/raw/../../x.zip '{URL}'",       # leaves raw/
            f"curl -fsSL -o .logs/HALOM-1/raw/sub/log.zip '{URL}'",       # not directly under raw/
            f"curl -fsSL -o .logs/HALOM-1/raw/log.zip '{URL}' && cat .logs/HALOM-1/raw/log.zip",
            f"curl -fsSL -o .logs/HALOM-1/raw/log.zip '{URL}'; echo hi",
            f"curl -d @.logs/HALOM-1/raw/log.zip -o .logs/HALOM-1/raw/a.zip '{URL}'",  # uploads it
            f"curl -T .logs/HALOM-1/raw/log.zip '{URL}'",
            "curl -fsSL -o .logs/HALOM-1/raw/log.zip http://example.com/log.zip",   # not https
            f"curl -fsSL -o .logs/HALOM-1/raw/log.zip '{URL}' '{URL}'",             # two URLs
            f"curl -fsSL -o .logs/HALOM-1/raw/log.zip \"$(cat .logs/HALOM-1/raw/x)\"",
            "cat .logs/HALOM-1/raw/log.txt",
            "unzip .logs/HALOM-1/raw/log.zip",
        ]:
            with self.subTest(command=command):
                self.assertEqual(run(command), "deny")

    def test_extract_script_still_allowed(self):
        self.assertIsNone(run(
            "python3 .github/log-analyser/scripts/logcat_extract.py"
            " .logs/HALOM-1/raw/log.zip -o .logs/HALOM-1/raw/extracted"))

    def test_jira_download_call_may_name_raw_path_only_for_that_call(self):
        ok = {"name": "downloadJiraIssueAttachment",
              "inputs": {"attachmentId": "1", "outputPath": ".logs/HALOM-1/raw/log.zip"}}
        self.assertIsNone(decision("executeRead", ok))
        elsewhere = {"name": "downloadJiraIssueAttachment", "inputs": {"attachmentId": "1", "outputPath": ".env"}}
        self.assertEqual(decision("executeRead", elsewhere), "deny")
        other_call = {"name": "getJiraIssue", "inputs": {"outputPath": ".logs/HALOM-1/raw/log.zip"}}
        self.assertEqual(decision("executeRead", other_call), "deny")


class PostedText(unittest.TestCase):
    def test_token_in_text_sent_through_executewrite_is_denied(self):
        body = {"name": "someBitbucketOperation", "inputs": {"description": "debug with token: abc123xyz"}}
        self.assertEqual(decision("executeWrite", body), "deny")

    def test_clean_text_through_executewrite_is_allowed(self):
        body = {"name": "someBitbucketOperation", "inputs": {"description": "Fixes the lock retry loop"}}
        self.assertIsNone(decision("executeWrite", body))

    def test_posting_operation_named_in_args_is_checked_even_via_executeread(self):
        body = {"name": "addOrEditJiraIssueComment", "inputs": {"body": "Authorization: Bearer abc123"}}
        self.assertEqual(decision("executeRead", body), "deny")

    def test_reads_with_token_looking_text_are_not_blocked(self):
        body = {"name": "getJiraIssue", "inputs": {"issueIdOrKey": "HALOM-1", "note": "token: abc"}}
        self.assertIsNone(decision("executeRead", body))


if __name__ == "__main__":
    unittest.main()
