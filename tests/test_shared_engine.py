import pathlib
import os
import io
import importlib.util
import subprocess
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_SOURCE = pathlib.Path(
    os.environ.get(
        "JAPANESE_READING_CORE_SOURCE",
        str(PROJECT_ROOT.parent / "japanese-language-core" / "src"),
    )
)
if CORE_SOURCE.is_dir():
    sys.path.insert(0, str(CORE_SOURCE))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utayomi_core import (  # noqa: E402
    SharedEngineUnavailableError,
    convert_to_ruby,
    convert_to_ruby_with_engine,
    main,
)


@unittest.skipUnless(
    CORE_SOURCE.is_dir() or importlib.util.find_spec("japanese_language_core.reading"),
    "需要本地 japanese-language-core/src 或已安装 japanese_language_core.reading",
)
class SharedEngineTests(unittest.TestCase):
    def test_auto_prefers_shared_engine_when_available(self):
        result = convert_to_ruby("雨が降り止む", engine="auto")
        self.assertIn("<ruby>降<rt>ふ</rt></ruby>り", result)

    def test_contextual_reading_comes_from_shared_engine(self):
        result = convert_to_ruby(
            "雨が降り止むまでは帰れない",
            engine="shared",
        )
        self.assertEqual(
            result,
            "<ruby>雨<rt>あめ</rt></ruby>が<ruby>降<rt>ふ</rt></ruby>り"
            "<ruby>止<rt>や</rt></ruby>むまでは<ruby>帰<rt>かえ</rt></ruby>れない",
        )

    def test_shared_engine_keeps_repeated_okurigana_outside_ruby(self):
        result = convert_to_ruby("人気の店で上手に歌う。", engine="shared")
        self.assertIn("<ruby>歌<rt>うた</rt></ruby>う", result)

    def test_legacy_engine_keeps_okurigana_outside_ruby(self):
        result = convert_to_ruby("歌う", engine="legacy")
        self.assertEqual(result, "<ruby>歌<rt>うた</rt></ruby>う")

    def test_legacy_engine_escapes_non_japanese_html(self):
        result = convert_to_ruby("A < B 歌う & C", engine="legacy")
        self.assertEqual(result, "A &lt; B <ruby>歌<rt>うた</rt></ruby>う &amp; C")

    def test_auto_requires_core_when_unavailable(self):
        with patch(
            "utayomi_core._convert_with_shared_engine",
            side_effect=SharedEngineUnavailableError("shared unavailable"),
        ):
            with self.assertRaises(SharedEngineUnavailableError):
                convert_to_ruby_with_engine("歌う", engine="auto")

    def test_auto_cli_errors_when_core_unavailable(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch(
            "utayomi_core._convert_with_shared_engine",
            side_effect=SharedEngineUnavailableError("shared unavailable"),
        ), patch.object(sys, "argv", ["utayomi_core.py", "--engine", "auto"]), patch.object(
            sys, "stdin", io.StringIO("歌う")
        ), patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as exc:
                main()
        self.assertEqual(2, exc.exception.code)
        self.assertIn("Error", stderr.getvalue())

    def test_cli_preserves_leading_and_trailing_line_structure(self):
        script = PROJECT_ROOT / "scripts" / "utayomi_core.py"
        environment = os.environ.copy()
        source_path = str(CORE_SOURCE)
        environment["PYTHONPATH"] = source_path + os.pathsep + environment.get("PYTHONPATH", "")
        source = "  \n夢ならば\n\n"
        completed = subprocess.run(
            [sys.executable, str(script), "--engine", "shared"],
            input=source,
            text=True,
            capture_output=True,
            env=environment,
            check=True,
        )
        self.assertEqual(
            completed.stdout,
            "  \n<ruby>夢<rt>ゆめ</rt></ruby>ならば\n\n",
        )


if __name__ == "__main__":
    unittest.main()
