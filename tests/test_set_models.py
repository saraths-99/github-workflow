"""Tests for set-models.py and models.json. Run: python3 -m unittest tests/test_set_models.py"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "set-models.py"
TABLE = json.loads((ROOT / "models.json").read_text())["providers"]


def lines(base):
    out = {}
    for f in sorted(list(base.glob(".github/agents/*.agent.md")) + list(base.glob(".github/prompts/*.prompt.md"))):
        for line in f.read_text().splitlines():
            if line.startswith("model: "):
                out[f.name] = line
    return out


def render(names):
    return "model: [" + ", ".join(f"'{n} (copilot)'" for n in names) + "]"


class SetModels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = Path(self.tmp.name)
        shutil.copytree(ROOT / ".github" / "agents", self.app / ".github" / "agents")
        shutil.copytree(ROOT / ".github" / "prompts", self.app / ".github" / "prompts")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, provider):
        return subprocess.run([sys.executable, str(SCRIPT), provider, str(self.app)], capture_output=True, text=True)

    def test_tiers_match_across_providers(self):
        self.assertEqual({k: set(v) for k, v in TABLE.items()}, {k: {"deep", "standard", "fast", "judge", "judge-fallback"} for k in TABLE})

    def test_tier_lists_are_distinct_so_a_line_names_one_tier(self):
        for provider, tiers in TABLE.items():
            texts = [render(v) for v in tiers.values()]
            self.assertEqual(len(texts), len(set(texts)), f"{provider} has two tiers with the same list")

    def test_test_related_agents_run_on_the_fast_tier(self):
        fast = render(TABLE["claude"]["fast"])
        got = lines(self.app)
        for name in ("qatalyst-test-writer.agent.md", "qatalyst-unit-test-writer.agent.md", "qatalyst-ble-protocol-test-writer.agent.md",
                     "qatalyst-security-test-writer.agent.md", "qatalyst-write-tests.prompt.md"):
            self.assertEqual(got[name], fast, name)

    def test_developer_runs_on_the_deep_tier(self):
        self.assertEqual(lines(self.app)["qatalyst-developer.agent.md"], render(TABLE["claude"]["deep"]))

    def test_fix_approver_runs_on_the_judge_tier_on_a_different_vendor(self):
        judge = render(TABLE["claude"]["judge"])
        self.assertEqual(lines(self.app)["qatalyst-fix-approver.agent.md"], judge)
        self.assertIn("GPT-5.3-Codex", judge)
        self.assertNotIn("Claude", judge)

    def test_fallback_approver_is_a_cheaper_gpt_model_on_its_own_tier(self):
        fb = render(TABLE["claude"]["judge-fallback"])
        self.assertEqual(lines(self.app)["qatalyst-fix-approver-fallback.agent.md"], fb)
        self.assertNotEqual(fb, render(TABLE["claude"]["judge"]))
        self.assertIn("GPT-6.1 Terra", fb)

    def test_gpt_install_keeps_the_judge_model(self):
        self.run_script("gpt")
        self.assertEqual(lines(self.app)["qatalyst-fix-approver.agent.md"], render(TABLE["gpt"]["judge"]))

    def test_no_claude_list_names_opus(self):
        self.assertNotIn("Opus", json.dumps(TABLE["claude"]))

    def test_checked_in_files_carry_claude_lists(self):
        allowed = {render(v) for v in TABLE["claude"].values()}
        self.assertTrue(lines(self.app))
        for name, line in lines(self.app).items():
            self.assertIn(line, allowed, name)

    def test_gpt_replaces_every_line_by_tier(self):
        before = lines(self.app)
        r = self.run_script("gpt")
        self.assertEqual(r.returncode, 0, r.stderr)
        tier_of = {render(v): t for t, v in TABLE["claude"].items()}
        for name, line in lines(self.app).items():
            self.assertEqual(line, render(TABLE["gpt"][tier_of[before[name]]]), name)
        self.assertNotIn("warning", r.stdout)

    def test_claude_is_a_no_op_and_gpt_can_switch_back(self):
        before = lines(self.app)
        self.assertEqual(self.run_script("claude").returncode, 0)
        self.assertEqual(lines(self.app), before)
        self.run_script("gpt")
        self.run_script("claude")
        self.assertEqual(lines(self.app), before)

    def test_unknown_line_is_left_alone_and_reported(self):
        f = self.app / ".github" / "agents" / "qatalyst-developer.agent.md"
        f.write_text(f.read_text().replace("model: [", "model: ['Some Other Model (copilot)', ", 1))
        r = self.run_script("gpt")
        self.assertIn("Some Other Model", f.read_text())
        self.assertIn("left alone", r.stdout)

    def test_unknown_provider_fails(self):
        self.assertNotEqual(self.run_script("gemini").returncode, 0)


if __name__ == "__main__":
    unittest.main()
