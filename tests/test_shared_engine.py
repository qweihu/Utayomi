import pathlib
import os
import importlib.util
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
)


@unittest.skipUnless(
    CORE_SOURCE.is_dir() or importlib.util.find_spec("japanese_language_core.reading"),
    "需要本地 japanese-language-core/src 或已安装 japanese_language_core.reading",
)
class SharedEngineTests(unittest.TestCase):
    def test_uses_shared_engine_when_available(self):
        result = convert_to_ruby("雨が降り止む")
        self.assertIn("<ruby>降<rt>ふ</rt></ruby>り", result)

    def test_contextual_reading_comes_from_shared_engine(self):
        result = convert_to_ruby("雨が降り止むまでは帰れない")
        self.assertEqual(
            result,
            "<ruby>雨<rt>あめ</rt></ruby>が<ruby>降<rt>ふ</rt></ruby>り"
            "<ruby>止<rt>や</rt></ruby>むまでは<ruby>帰<rt>かえ</rt></ruby>れない",
        )

    def test_shared_engine_keeps_repeated_okurigana_outside_ruby(self):
        result = convert_to_ruby("人気の店で上手に歌う。")
        self.assertIn("<ruby>歌<rt>うた</rt></ruby>う", result)

    def test_auto_requires_core_when_unavailable(self):
        with patch(
            "utayomi_core._convert_with_shared_engine",
            side_effect=SharedEngineUnavailableError("shared unavailable"),
        ):
            with self.assertRaises(SharedEngineUnavailableError):
                convert_to_ruby("歌う")

if __name__ == "__main__":
    unittest.main()
