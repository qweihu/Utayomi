import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from utayomi import main, process_lyrics  # noqa: E402


class UtayomiEntrypointTests(unittest.TestCase):
    def test_processes_in_memory_and_uses_requested_language(self):
        document = process_lyrics(
            "星明かり\nExample Artist\n\n星明かりが窓辺を照らす\n明日へ歩き出す",
            translations=["Starlight shines by the window", "I walk toward tomorrow"],
            language="de",
        )
        self.assertIn('lang="de"', document.html)
        self.assertIn("<ruby>", document.html)
        self.assertIn("Starlight shines by the window", document.html)
        self.assertNotIn(".txt", document.html)

    def test_default_cli_emits_html_to_stdout(self):
        stdin = io.StringIO("星明かりが窓辺を照らす")
        stdout = io.StringIO()
        with patch("sys.stdin", stdin), contextlib.redirect_stdout(stdout):
            status = main([])
        self.assertEqual(status, 0)
        self.assertIn("<!doctype html>", stdout.getvalue())

    def test_file_input_creates_timestamped_sibling(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "lyrics.txt"
            source.write_text("星明かりが窓辺を照らす", encoding="utf-8")
            status = main(["--file", str(source)])
            self.assertEqual(status, 0)
            outputs = [path for path in Path(directory).iterdir() if path != source]
            self.assertEqual(len(outputs), 1)
            self.assertRegex(outputs[0].name, r"^lyrics\.\d{8}-\d{6}(?:-\d+)?\.html$")


if __name__ == "__main__":
    unittest.main()
