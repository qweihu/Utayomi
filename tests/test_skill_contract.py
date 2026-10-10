from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_skill_declares_one_default_html_workflow(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        prompt = (ROOT / "PROMPT.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("self-contained HTML", skill)
        self.assertIn("Use `scripts/utayomi.py --agent-json`", skill)
        self.assertIn("默认生成独立 HTML", prompt)
        self.assertIn("return HTML", metadata)

    def test_skill_hides_removed_complexity(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("legacy", skill.lower())
        self.assertNotIn("--output", skill)
        self.assertIn("Do not generate Anki cards", skill)


if __name__ == "__main__":
    unittest.main()
