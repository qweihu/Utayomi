import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_html import render_html_from_markdown  # noqa: E402

SAMPLE_MD = (
    "**歌曲: 未命名歌曲 / 未知歌手**\n"
    "\n"
    "いっせーのーせで<ruby>踏み込む<rt>ふみこむ</rt></ruby>ゴーライン\n"
    "喊着“一二预备”踏进这条终点线\n"
    "\n"
    "<ruby>僕<rt>ぼく</rt></ruby>らは<ruby>何<rt>なに</rt></ruby>もまだ<ruby>知ら<rt>しら</rt></ruby>ぬ\n"
    "我们还什么都不知道\n"
)

ROMAJI_MD = (
    "**歌曲: 夢 / 测试**\n"
    "\n"
    "<ruby>夢<rt>yume</rt></ruby><ruby>なら<rt>nara</rt></ruby><ruby>ば<rt>ba</rt></ruby>\n"
    "如果是梦\n"
)


class BuildHtmlTests(unittest.TestCase):
    def build(self, content=SAMPLE_MD):
        return render_html_from_markdown(content)

    def test_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            self.build("  \n  ")

    def test_header_and_pairs(self):
        page = self.build()
        self.assertIn('<span class="title">未命名歌曲</span>', page)
        self.assertIn('<span class="artist">未知歌手</span>', page)
        self.assertEqual(page.count('<div class="pair">'), 2)
        self.assertIn("<ruby>踏み込む<rt>ふみこむ</rt></ruby>", page)
        self.assertIn("喊着“一二预备”踏进这条终点线", page)

    def test_missing_header_falls_back_to_defaults(self):
        page = self.build("<ruby>夢<rt>ゆめ</rt></ruby>\n梦\n")
        self.assertIn('<span class="title">Untitled Song</span>', page)
        self.assertIn('<span class="artist">Unknown Artist</span>', page)

    def test_escapes_non_ruby_html(self):
        content = "**歌曲: A / B**\n\n<script>alert(1)</script>歌<ruby>詞<rt>し</rt></ruby>\n译<b>文</b>\n"
        page = self.build(content)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("<ruby>詞<rt>し</rt></ruby>", page)
        self.assertIn("译&lt;b&gt;文&lt;/b&gt;", page)

    def test_romaji_mode_marks_body(self):
        page = self.build(ROMAJI_MD)
        self.assertIn('<body class="romaji">', page)

    def test_self_contained_with_themes_and_export(self):
        page = self.build()
        # 导出按钮与主题切换存在，且只用浏览器内置能力
        self.assertIn('id="export"', page)
        self.assertIn('id="themes"', page)
        self.assertIn("XMLSerializer", page)
        self.assertIn("canvas", page)
        # 四个配色主题都可切换
        for theme in ("matcha", "umi", "akane", "yoru"):
            self.assertIn(f'data-theme="{theme}"', page)
        # 工具栏在 #card 之外，导出截图只克隆 #card，因此不会带上切换按钮
        self.assertGreater(page.index('class="toolbar"'), page.index("</main>"))
        self.assertIn('getElementById("card")', page)
        # 不引用任何外部资源
        for token in ("src=\"http", "href=\"http", "@import", "url(http", "<link"):
            self.assertNotIn(token, page)


if __name__ == "__main__":
    unittest.main()
