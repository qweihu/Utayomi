import pathlib
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "save_markdown.py"


class ExportTests(unittest.TestCase):
    def run_export(self, output, *options, content="<ruby>夢<rt>ゆめ</rt></ruby>"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--output", str(output), *options],
            input=content,
            text=True,
            capture_output=True,
        )

    def test_requires_absolute_path(self):
        completed = self.run_export(pathlib.Path("lesson.md"))
        self.assertEqual(completed.returncode, 2)
        self.assertIn("绝对路径", completed.stderr)

    def test_requires_explicit_parent_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "nested" / "lesson.md"
            completed = self.run_export(output)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(output.exists())
            self.assertIn("--create-parent", completed.stderr)

    def test_create_parent_and_protect_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "nested" / "lesson.md"
            created = self.run_export(output, "--create-parent", content="first")
            self.assertEqual(created.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "first")

            blocked = self.run_export(output, content="second")
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "first")

            overwritten = self.run_export(output, "--overwrite", content="second")
            self.assertEqual(overwritten.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "second")


if __name__ == "__main__":
    unittest.main()
