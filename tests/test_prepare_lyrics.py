import json
import pathlib
import subprocess
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from prepare_lyrics import clean_markup, prepare_text  # noqa: E402


class PrepareLyricsTests(unittest.TestCase):
    def test_removes_markup_scripts_styles_and_ruby_readings(self):
        raw = """
        <article>
          <h1>歌曲名：星空</h1>
          <p>歌手：示例歌手</p>
          <p><ruby>夜<rt>よる</rt></ruby>の風<br>星を見上げる</p>
          <script>不要输出的广告</script>
          <style>.noise { display: none; }</style>
        </article>
        """

        prepared = prepare_text(raw)

        self.assertEqual(prepared["title"], "星空")
        self.assertEqual(prepared["artist"], "示例歌手")
        self.assertEqual(prepared["lyrics"], "夜の風\n星を見上げる")
        self.assertNotIn("<", prepared["lyrics"])
        self.assertNotIn("不要输出", prepared["lyrics"])

    def test_finds_unlabeled_title_and_artist_line_in_full_input(self):
        raw = """
        页面复制时带入的说明
        夜明け / 例示歌手
        静かな風
        朝の光
        """

        prepared = prepare_text(raw)

        self.assertEqual(prepared["title"], "夜明け")
        self.assertEqual(prepared["artist"], "例示歌手")
        self.assertEqual(prepared["lyrics"], "页面复制时带入的说明\n静かな風\n朝の光")

    def test_auto_detects_short_title_and_artist_lines(self):
        raw = "星空\n示例歌手\n静かな夜に\n星を見上げる\n"

        prepared = prepare_text(raw)

        self.assertEqual(prepared["title"], "星空")
        self.assertEqual(prepared["artist"], "示例歌手")
        self.assertEqual(prepared["lyrics"], "静かな夜に\n星を見上げる")

    def test_html_heading_structure_supports_short_metadata_lines(self):
        raw = "<h1>ほしのうた</h1><p>あいみょん</p><p>静かな夜に</p><p>星を見上げる</p>"

        prepared = prepare_text(raw)

        self.assertEqual(prepared["title"], "ほしのうた")
        self.assertEqual(prepared["artist"], "あいみょん")
        self.assertEqual(prepared["lyrics"], "静かな夜に\n星を見上げる")

    def test_does_not_remove_short_lyric_lines_without_header_structure(self):
        raw = "愛してる\n君のこと\n静かな夜に\n星を見上げる\n"

        prepared = prepare_text(raw)

        self.assertIsNone(prepared["title"])
        self.assertIsNone(prepared["artist"])
        self.assertEqual(prepared["lyrics"], raw.strip())

    def test_opt_in_header_lines_keep_title_and_artist_out_of_lyrics(self):
        raw = "星空\n示例歌手\n静かな夜に\n星を見上げる\n"

        prepared = prepare_text(raw, header_lines=2)

        self.assertEqual(prepared["title"], "星空")
        self.assertEqual(prepared["artist"], "示例歌手")
        self.assertEqual(prepared["lyrics"], "静かな夜に\n星を見上げる")

    def test_decodes_entities_and_keeps_plain_text_lines(self):
        raw = "歌曲名: 星 &amp; 月\n歌手: 示例\n静かな&nbsp;夜"

        prepared = prepare_text(raw)

        self.assertEqual(prepared["title"], "星 & 月")
        self.assertEqual(prepared["artist"], "示例")
        self.assertEqual(prepared["lyrics"], "静かな 夜")

    def test_json_cli_returns_structured_result(self):
        completed = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/prepare_lyrics.py"), "--json"],
            input="歌曲名：测试\n歌手：歌手\n歌詞です\n",
            text=True,
            capture_output=True,
            check=True,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(result, {"title": "测试", "artist": "歌手", "lyrics": "歌詞です"})


if __name__ == "__main__":
    unittest.main()
