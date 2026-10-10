from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from install_utayomi_skill import install  # noqa: E402


class InstallSkillTests(unittest.TestCase):
    def test_installs_skill_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "skills" / "utayomi"
            target = install(destination, force=False)
            self.assertEqual(target, destination.resolve())
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "agents" / "openai.yaml").is_file())
            self.assertTrue((target / "scripts" / "utayomi.py").is_file())
            self.assertTrue((target / "requirements.txt").is_file())
            self.assertFalse((target / "scripts" / "run_tests.py").exists())

    def test_refuses_existing_install_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "utayomi"
            install(destination, force=False)
            with self.assertRaises(RuntimeError):
                install(destination, force=False)


if __name__ == "__main__":
    unittest.main()
