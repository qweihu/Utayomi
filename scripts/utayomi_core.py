"""Internal shared-engine adapter used by the unified Utayomi entry point."""

import html
import re


RUBY_BLOCK_RE = re.compile(r"<ruby>.*?</ruby>")


class SharedEngineUnavailableError(RuntimeError):
    """The optional shared package or its runtime dependencies are absent."""


def _escape(value):
    return html.escape(value, quote=False)


def _ruby(surface, reading):
    if not surface or not reading:
        return _escape(surface)
    return f"<ruby>{_escape(surface)}<rt>{_escape(reading)}</rt></ruby>"


def _render_shared_hiragana(token, align_reading):
    surface = token.orig
    reading = token.hira
    if not has_kanji(surface) or not reading:
        return _escape(surface)
    parts = align_reading(surface, reading)
    if any(has_kanji(part) and not part_reading for part, part_reading in parts):
        parts = [(surface, reading)]
    return "".join(
        _ruby(part, part_reading)
        if part_reading and has_kanji(part)
        else _escape(part)
        for part, part_reading in parts
    )


def _render_shared_token(token, mode, align_reading):
    if mode == "romaji":
        if has_japanese(token.orig) and token.hepburn:
            return _ruby(token.orig, token.hepburn)
        return _escape(token.orig)
    return _render_shared_hiragana(token, align_reading)


def _convert_with_shared_engine(text, mode):
    try:
        from japanese_language_core.reading import align_reading, create_engine
    except ImportError as exc:
        raise SharedEngineUnavailableError(
            "未找到 japanese_language_core.reading；请安装 japanese-language-core 或设置 "
            "PYTHONPATH 指向其 src 目录"
        ) from exc

    try:
        engine = create_engine("auto")
    except Exception as exc:
        raise SharedEngineUnavailableError(f"共享日语读音引擎不可用: {exc}") from exc
    try:
        tokens = tuple(engine.tokens(text))
    except Exception as exc:
        raise RuntimeError(f"共享日语读音引擎处理失败: {exc}") from exc
    if "".join(token.orig for token in tokens) != text:
        raise RuntimeError("共享引擎没有保留歌词原文")
    reading_attr = "hepburn" if mode == "romaji" else "hira"
    missing = [
        token.orig for token in tokens
        if has_kanji(token.orig) and not getattr(token, reading_attr)
    ]
    if missing:
        raise RuntimeError(f"共享引擎没有提供汉字读音: {missing[0]}")

    rendered = "".join(
        _render_shared_token(token, mode, align_reading) for token in tokens
    )
    visible = html.unescape(
        re.sub(r"</?ruby>|<rt>.*?</rt>", "", rendered)
    )
    if visible != text:
        raise RuntimeError("Ruby 标注改变了歌词原文")
    unannotated = RUBY_BLOCK_RE.sub("", rendered)
    if has_kanji(html.unescape(unannotated)):
        raise RuntimeError("歌词中仍有未注音的汉字")
    if rendered.count("<ruby>") != rendered.count("</ruby>") or rendered.count(
        "<rt>"
    ) != rendered.count("</rt>"):
        raise RuntimeError("Ruby 标注标签不完整")
    return rendered


def has_kanji(text):
    """检查文本中是否包含日文汉字"""
    return bool(re.search(r'[\u4e00-\u9faf]', text))


def has_japanese(text):
    """检查文本中是否包含任何日文字符（汉字、平假名、片假名）"""
    return bool(re.search(r'[\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]', text))


def convert_to_ruby(text, mode='hiragana'):
    """Annotate with the shared reading engine.

    Engine selection belongs to ``japanese-language-core``. Utayomi exposes
    only the reading mode because callers should not need to choose a backend.
    """

    if mode not in {"hiragana", "romaji"}:
        raise ValueError(f"不支持的注音模式: {mode}")
    return _convert_with_shared_engine(text, mode)
