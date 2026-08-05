#!/usr/bin/env python3
"""
Utayomi - 日语歌词注音工具

用法：
    # 从标准输入注音
    echo "歌词文本" | .venv/bin/python scripts/utayomi_core.py
    
    # 从文件注音
    .venv/bin/python scripts/utayomi_core.py < lyrics.txt
    
    # 罗马音模式
    .venv/bin/python scripts/utayomi_core.py --romaji < lyrics.txt
"""
import sys
import re
import argparse
import html
from types import SimpleNamespace
import pykakasi
import fugashi


KANA_RUN_RE = re.compile(r"[ぁ-ゖァ-ヺヽヾー]+")


class SharedEngineUnavailableError(RuntimeError):
    """The optional shared package or its runtime dependencies are absent."""


def _escape(value):
    return html.escape(value, quote=False)


def _ruby(surface, reading):
    if not surface or not reading:
        return _escape(surface)
    return f"<ruby>{_escape(surface)}<rt>{_escape(reading)}</rt></ruby>"


def _render_shared_hiragana(token):
    surface = token.orig
    reading = token.hira
    if not has_kanji(surface) or not reading:
        return _escape(surface)

    kana_runs = list(KANA_RUN_RE.finditer(surface))
    if not kana_runs:
        return _ruby(surface, reading)

    pieces = []
    surface_cursor = 0
    reading_cursor = 0
    for kana_match in kana_runs:
        before = surface[surface_cursor:kana_match.start()]
        if before:
            if has_kanji(before):
                kana_hint = kana_match.group(0)
                reading_index = reading.find(kana_hint, reading_cursor)
                while reading_index >= 0 and reading_index <= reading_cursor:
                    reading_index = reading.find(kana_hint, reading_index + 1)
                if reading_index < 0:
                    return _ruby(surface, reading)
                pieces.append(_ruby(before, reading[reading_cursor:reading_index]))
                reading_cursor = reading_index
            else:
                pieces.append(_escape(before))

        kana_text = kana_match.group(0)
        pieces.append(_escape(kana_text))
        if reading.startswith(kana_text, reading_cursor):
            reading_cursor += len(kana_text)
        else:
            reading_index = reading.find(kana_text, reading_cursor)
            if reading_index < 0:
                return _ruby(surface, reading)
            reading_cursor = reading_index + len(kana_text)
        surface_cursor = kana_match.end()

    after = surface[surface_cursor:]
    if after:
        if has_kanji(after):
            if reading_cursor >= len(reading):
                return _ruby(surface, reading)
            pieces.append(_ruby(after, reading[reading_cursor:]))
        else:
            pieces.append(_escape(after))
    return "".join(pieces) if pieces else _ruby(surface, reading)


def _render_shared_token(token, mode):
    if mode == "romaji":
        if has_japanese(token.orig) and token.hepburn:
            return _ruby(token.orig, token.hepburn)
        return _escape(token.orig)
    return _render_shared_hiragana(token)


def _convert_with_shared_engine(text, mode):
    try:
        from japanese_reading_core import create_engine
    except ImportError as exc:
        raise SharedEngineUnavailableError(
            "未找到 japanese_reading_core；请安装 japanese-language-core 或设置 "
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
    return "".join(_render_shared_token(token, mode) for token in tokens), getattr(engine, "name", "shared")


def has_kanji(text):
    """检查文本中是否包含日文汉字"""
    return bool(re.search(r'[\u4e00-\u9faf]', text))


def has_japanese(text):
    """检查文本中是否包含任何日文字符（汉字、平假名、片假名）"""
    return bool(re.search(r'[\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]', text))


def _convert_to_ruby_legacy(text, mode='hiragana'):
    """
    将日文文本转换为带有 <ruby> 标签的格式
    
    Args:
        text: 输入文本（应为已清洗的纯文本）
        mode: 'hiragana' 或 'romaji'，默认为平假名
    """
    tagger = fugashi.Tagger()
    kks = pykakasi.Kakasi()
    
    lines = text.split('\n')
    result_lines = []
    
    for line in lines:
        if not line.strip():
            result_lines.append(_escape(line))
            continue
            
        result_line = ""
        for chunk in re.split(r"(\s+)", line):
            if not chunk:
                continue
            if chunk.isspace():
                result_line += _escape(chunk)
                continue

            words = tagger(chunk)
            for word in words:
                surface = word.surface
            
                if mode == 'romaji':
                    # 罗马音模式：对包含日文的词汇进行罗马音转换
                    if not has_japanese(surface):
                        result_line += _escape(surface)
                        continue
                
                    converted = kks.convert(surface)
                    for item in converted:
                        result_line += _render_shared_token(
                            SimpleNamespace(
                                orig=str(item.get('orig', '')),
                                hira=str(item.get('hira', '')),
                                hepburn=str(item.get('hepburn', '')),
                            ),
                            mode,
                        )
                else:
                    # 平假名模式：仅对包含汉字的词汇进行转换
                    if not has_kanji(surface):
                        result_line += _escape(surface)
                        continue
                
                    # 使用共享渲染器处理送假名、空白和 HTML 转义
                    converted = kks.convert(surface)
                
                    for item in converted:
                        result_line += _render_shared_token(
                            SimpleNamespace(
                                orig=str(item.get('orig', '')),
                                hira=str(item.get('hira', '')),
                                hepburn=str(item.get('hepburn', '')),
                            ),
                            mode,
                        )
                        
        result_lines.append(result_line)
        
    return '\n'.join(result_lines)


def convert_to_ruby_with_engine(text, mode='hiragana', engine='auto'):
    """Annotate with the shared engine when available.

    ``auto`` prefers ``japanese_reading_core`` and falls back to the original
    Fugashi/PyKakasi implementation for standalone legacy installations.
    ``shared`` is strict and is used by the cross-project contract tests.
    """

    if engine not in {'auto', 'shared', 'legacy'}:
        raise ValueError("engine must be 'auto', 'shared', or 'legacy'")
    if engine == 'legacy':
        return _convert_to_ruby_legacy(text, mode), 'legacy'
    try:
        return _convert_with_shared_engine(text, mode)
    except SharedEngineUnavailableError:
        if engine == 'shared':
            raise
        return _convert_to_ruby_legacy(text, mode), 'legacy'


def convert_to_ruby(text, mode='hiragana', engine='auto'):
    """Return annotated text while preserving the historical API."""

    return convert_to_ruby_with_engine(text, mode=mode, engine=engine)[0]


def main():
    parser = argparse.ArgumentParser(
        description='Utayomi - 日语歌词注音工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例：
  echo "夢ならばどれほどよかったでしょう" | .venv/bin/python scripts/utayomi_core.py
  cat lyrics.txt | .venv/bin/python scripts/utayomi_core.py --romaji
        '''
    )
    
    parser.add_argument(
        '--romaji', '-r',
        action='store_true',
        help='使用罗马音标注（默认使用平假名）'
    )
    parser.add_argument(
        '--engine',
        choices=('auto', 'shared', 'legacy'),
        default='auto',
        help='读音引擎：auto 优先共享 japanese_reading_core，legacy 使用旧版 Fugashi/PyKakasi',
    )
    
    args = parser.parse_args()
    
    # 从标准输入读取；仅用 strip 判断空输入，不改写用户原文。
    input_content = sys.stdin.read()
    
    if not input_content.strip():
        print("Error: 没有输入内容。请通过管道传入文本。", file=sys.stderr)
        print("用法: echo '歌词' | .venv/bin/python scripts/utayomi_core.py", file=sys.stderr)
        sys.exit(1)
    
    # 转换注音
    mode = 'romaji' if args.romaji else 'hiragana'
    try:
        ruby_text, selected_engine = convert_to_ruby_with_engine(
            input_content,
            mode=mode,
            engine=args.engine,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
    
    if args.engine == 'auto' and selected_engine == 'legacy':
        print(
            "Warning: japanese_reading_core 不可用，已回退 legacy；请安装 japanese-language-core 并使用 --engine shared。",
            file=sys.stderr,
        )

    # 输出结果，不额外添加换行，保持输入的首尾换行结构。
    sys.stdout.write(ruby_text)


if __name__ == "__main__":
    main()
