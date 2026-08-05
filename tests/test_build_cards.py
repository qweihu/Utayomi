import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_cards import main  # noqa: E402


class BuildCardsTests(unittest.TestCase):
    def test_tsv_output(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer), unittest.mock.patch.object(
            sys, "stdin", io.StringIO("日本語を勉強する。\n")
        ):
            rc = main(["--format", "tsv"])
        self.assertEqual(0, rc)
        lines = buffer.getvalue().splitlines()
        self.assertTrue(lines[0].startswith("Expression"))
        self.assertTrue(any("日本語" in line for line in lines))

    def test_payload_output_with_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            lyrics = Path(directory) / "lyrics.txt"
            translations = Path(directory) / "tr.txt"
            lyrics.write_text("日本語を勉強する。\n", encoding="utf-8")
            translations.write_text("学习日语。\n", encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = main(
                    [
                        "--input",
                        str(lyrics),
                        "--translation",
                        str(translations),
                        "--format",
                        "payload",
                        "--deck",
                        "Lyrics",
                        "--model",
                        "Basic",
                    ]
                )
            self.assertEqual(0, rc)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(1, len(payload))
            note = payload[0]["params"]["note"]
            self.assertEqual("Lyrics", note["deckName"])
            self.assertEqual("学习日语。", note["fields"]["Translation"])


if __name__ == "__main__":
    unittest.main()
