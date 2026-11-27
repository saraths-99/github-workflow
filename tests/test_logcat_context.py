"""Tests for .github/log-analyser/scripts/logcat_context.py. Run: python3 -m unittest tests/test_logcat_context.py"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / ".github" / "log-analyser" / "scripts" / "logcat_context.py"
PKG = "com.example.app"

# threadtime lines: the app is pid 1000; 2000 is the Bluetooth stack; 3000 is system_server.
LOG = "\n".join([
    "01-01 10:00:00.000  3000  3000 I ActivityManager: Start proc 1000:com.example.app/u0a1 for activity",
    "01-01 10:00:01.000  1000  1000 I App: versionName=4.2.0 versionCode=420",
    "01-01 10:00:02.000  1000  1000 I App: Build.MODEL=Pixel 8 Android version 15",
    "01-01 10:00:03.000  1000  1000 I Lock: firmware version 2.1.7 reported",
    # an earlier, healthy connection: noise-tag lines that logcat_trim drops
    "01-01 10:10:00.000  2000  2000 I BtGatt.GattService: onClientConnectionState status=0 connected=true",
    # the lead-up to the issue, in the Bluetooth process (not the app's)
    "01-01 10:59:30.000  2000  2000 I BtGatt.GattService: onClientConnectionState status=0 connected=true",
    "01-01 10:59:40.000  1000  1000 I Ble: sending command 0x10 token=abc123secret",
    "01-01 10:59:50.000  2000  2000 W bt_btm: disconnect reason=0x08 status=133",
    "01-01 11:00:00.000  1000  1000 E Ble: command timed out status=133",
    "01-01 11:00:05.000  3000  3000 I ActivityManager: Process com.example.app (pid 1000) has died",
    "01-01 11:00:06.000  3000  3000 I ActivityManager: Start proc 1111:com.example.app/u0a1 for service",
    # a long silence, then more of it
    "01-01 11:05:00.000  1111  1111 E Ble: command timed out status=133",
    "01-01 11:05:01.000  1111  1111 W Ble: reach me at dev@example.com",
    "not a log line at all",
]) + "\n"


class Context(unittest.TestCase):
    def run_it(self, *args, log=LOG):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "extracted.log"
            p.write_text(log)
            return subprocess.run([sys.executable, str(SCRIPT), str(p), "--package", PKG, *args], capture_output=True, text=True)

    def test_sections_and_boundaries(self):
        r = self.run_it("--at", "11:00:00")
        self.assertEqual(r.returncode, 0, r.stderr)
        for section in ("## Log boundaries", "## Environment", "## Process lifecycle", "## Lead-up and aftermath", "## How often"):
            self.assertIn(section, r.stdout)
        self.assertIn("App process(es): 1000, 1111", r.stdout)
        self.assertIn("(1 unreadable)", r.stdout)
        self.assertIn("Line nearest the issue time: 01-01 11:00:00.000 (0 s away)", r.stdout)
        self.assertIn("Gap of 597 s between 01-01 10:00:03.000 and 01-01 10:10:00.000", r.stdout)
        self.assertIn("Gap of 2970 s between 01-01 10:10:00.000 and 01-01 10:59:30.000", r.stdout)
        self.assertIn("Gap of 294 s between 01-01 11:00:06.000 and 01-01 11:05:00.000", r.stdout)

    def test_environment_and_lifecycle_from_outside_any_window(self):
        r = self.run_it("--at", "11:00:00")
        self.assertIn("versionName=4.2.0", r.stdout)
        self.assertIn("firmware version 2.1.7", r.stdout)
        self.assertIn("Process com.example.app (pid 1000) has died", r.stdout)
        self.assertIn("Start proc 1111:com.example.app", r.stdout)

    def test_leadup_includes_other_processes_and_noise_tags(self):
        r = self.run_it("--at", "11:00:00", "--tag", "BtGatt.GattService", "--tag", "bt_btm")
        lead = r.stdout.split("## Lead-up and aftermath")[1].split("## How often")[0]
        self.assertIn("S 01-01 10:59:30.000 2000", lead)           # the Bluetooth process, a noise tag
        self.assertIn("disconnect reason=0x08 status=133", lead)
        self.assertNotIn("10:10:00", lead)                         # outside the 300 s lead-up

    def test_default_leadup_is_every_warning_and_error_of_any_process(self):
        r = self.run_it("--at", "11:00:00")
        lead = r.stdout.split("## Lead-up and aftermath")[1].split("## How often")[0]
        self.assertIn("W bt_btm", lead)
        self.assertIn("E Ble: command timed out", lead)
        self.assertNotIn("I Ble: sending command", lead)

    def test_frequency_shows_chronic_versus_new(self):
        r = self.run_it("--at", "11:00:00", "--grep", r"status=133")
        freq = r.stdout.split("## How often")[1]
        self.assertIn("Pattern status=133", freq)
        self.assertIn("3 lines, first 01-01 10:59, last 01-01 11:05, in 3 different minutes", freq)
        self.assertIn("Errors from the app process", freq)

    def test_redaction_and_cap(self):
        r = self.run_it("--at", "11:00:00", "--lead", "1000", "--max-lines", "2")
        self.assertNotIn("abc123secret", r.stdout)
        self.assertNotIn("dev@example.com", r.stdout)
        self.assertIn("# redacted: 1 tokens, 0 JWTs, 1 emails", r.stdout)
        self.assertIn("more lines not shown", r.stdout)

    def test_no_time_given_says_so(self):
        r = self.run_it()
        self.assertIn("No --at given, so no window.", r.stdout)

    def test_empty_input_does_not_crash(self):
        r = self.run_it(log="nothing parseable\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("No readable log lines.", r.stdout)


if __name__ == "__main__":
    unittest.main()
