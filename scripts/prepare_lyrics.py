#!/usr/bin/env python3
"""Prepare user-provided lyric text for annotation.

This module deliberately has no network capability. It accepts either plain
text or pasted HTML, removes markup-only noise, and conservatively extracts
song metadata from labels or strong header structure.

Examples:
    cat pasted-lyrics.txt | .venv/bin/python scripts/prepare_lyrics.py
    cat pasted-lyrics.txt | .venv/bin/python scripts/prepare_lyrics.py --json
"""

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser


BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "dd",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}

SKIP_TAGS = {"canvas", "iframe", "noscript", "script", "style", "svg", "template"}
RUBY_ANNOTATION_TAGS = {"rp", "rt"}

TITLE_LABELS = r"歌曲名称|歌曲名|歌名|曲名|标题|song\s*title|title|song"
ARTIST_LABELS = r"歌手名称|歌手名|歌手|演唱者|艺术家|artist|アーティスト"
COMBINED_SEPARATOR = r"\s*(?:/|／|\\|｜|·|•| - | – | — )\s*"
HEADER_MAX_LENGTH = 40
ARTIST_MAX_LENGTH = 24
NON_METADATA_LINES = {
    "artist",
    "lyrics",
    "menu",
    "share",
    "song",
    "歌詞",
    "歌詞一覧",
    "歌曲名",
    "歌名",
    "歌手",
    "分享",
    "登录",
    "メニュー",
    "ログイン",
}


class _MarkupExtractor(HTMLParser):
    """Turn pasted markup into text while preserving block boundaries."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.annotation_depth = 0

    def _newline(self):
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in RUBY_ANNOTATION_TAGS:
            self.annotation_depth += 1
            return
        if self.annotation_depth:
            return
        if tag == "br":
            self._newline()
        elif tag in BLOCK_TAGS:
            self._newline()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in RUBY_ANNOTATION_TAGS:
            if self.annotation_depth:
                self.annotation_depth -= 1
            return
        if self.annotation_depth:
            return
        if tag in BLOCK_TAGS:
            self._newline()

    def handle_data(self, data):
        if not self.skip_depth and not self.annotation_depth:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def clean_markup(raw_text):
    """Remove HTML markup and normalize whitespace without using the network."""

    parser = _MarkupExtractor()
    parser.feed(raw_text)
    parser.close()
    text = html.unescape(parser.text())
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []
    previous_blank = False
    for raw_line in text.split("\n"):
        line = re.sub(r"[ \t\f\v\u00a0]+", " ", raw_line).strip()
        if not line:
            if not previous_blank and cleaned_lines:
                cleaned_lines.append("")
            previous_blank = True
            continue
        cleaned_lines.append(line)
        previous_blank = False

    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    return "\n".join(cleaned_lines)


def _label_match(line, labels):
    return re.match(rf"^\s*(?:{labels})\s*[:：=]\s*(.*?)\s*$", line, re.IGNORECASE)


def _combined_match(line):
    if len(line) > 120:
        return None
    parts = re.split(COMBINED_SEPARATOR, line, maxsplit=1)
    if len(parts) != 2 or not all(parts):
        return None
    left, right = (part.strip(" \t-—–:：") for part in parts)
    if not left or not right:
        return None
    return left, right


def _has_japanese(text):
    return bool(re.search(r"[\u4e00-\u9faf\u3040-\u309f\u30a0-\u30ff]", text))


def _is_short_header_line(line):
    if not line or len(line) > HEADER_MAX_LENGTH or line.casefold() in NON_METADATA_LINES:
        return False
    if re.search(r"[、。，．。！？!?；;:：]", line):
        return False
    if re.search(r"[/／\\｜·•]|(?:\s[-–—]\s)", line):
        return False
    return True


def _is_artist_like(line):
    """Return whether a short line looks more like a person/group name."""

    if len(line) > ARTIST_MAX_LENGTH or re.search(r"[、。，．。！？!?；;:：]", line):
        return False
    if re.search(r"[/／\\｜·•]|(?:\s[-–—]\s)", line):
        return False
    if not re.search(r"[\u3040-\u309f]", line):
        return True
    return not re.search(r"(?:る|た|て|ない|よ|ね|の|に|を|が|は|へ|で|と)$", line)


def _auto_header_indexes(lines, raw_text):
    """Find a likely title/artist pair without deleting ordinary lyric lines."""

    nonempty_indexes = [index for index, line in enumerate(lines) if line.strip()]
    if len(nonempty_indexes) < 3:
        return None

    title_index, artist_index = nonempty_indexes[:2]
    title_line = lines[title_index].strip()
    artist_line = lines[artist_index].strip()
    if not (_is_short_header_line(title_line) and _is_short_header_line(artist_line)):
        return None

    lyric_lines = [lines[index] for index in nonempty_indexes[2:]]
    if sum(_has_japanese(line) for line in lyric_lines[:6]) < 2:
        return None

    has_heading = bool(
        re.search(r"<\s*(?:title|h1|h2|h3)\b", raw_text, re.IGNORECASE)
    )
    has_blank_after_header = (
        artist_index + 1 < len(lines) and not lines[artist_index + 1].strip()
    )
    has_name_like_artist = _is_artist_like(artist_line)

    # A blank separator or HTML heading is a strong structural signal. For
    # plain text, a short name-like second line supports the documented
    # title-then-artist convention.
    if has_heading or has_blank_after_header or has_name_like_artist:
        return title_index, artist_index
    return None


def prepare_text(raw_text, header_lines=None):
    """Return cleaned lyrics and conservatively detected metadata.

    Explicit labels are preferred. An unlabeled two-part line such as
    ``Song Title / Artist`` is accepted as a fallback because it is the
    documented output format of this project. By default, a short first line,
    a short name-like second line, and at least two lyric-looking lines after
    them are treated as a likely header. HTML heading structure or a blank
    separator makes that inference stronger. When ``header_lines=2`` is
    supplied, the first two non-empty lines are treated as title and artist;
    when ``header_lines=0`` is supplied, automatic header detection is
    disabled. Ambiguous lyric lines are kept.
    """

    cleaned = clean_markup(raw_text)
    lines = cleaned.split("\n") if cleaned else []
    title = None
    artist = None
    metadata_indexes = set()

    for index, line in enumerate(lines):
        title_match = _label_match(line, TITLE_LABELS)
        artist_match = _label_match(line, ARTIST_LABELS)
        if title_match and title_match.group(1):
            title = title_match.group(1).strip()
            metadata_indexes.add(index)
        if artist_match and artist_match.group(1):
            artist = artist_match.group(1).strip()
            metadata_indexes.add(index)

    if not title or not artist:
        nonempty_indexes = [index for index, line in enumerate(lines) if line.strip()]
        if header_lines == 2 and len(nonempty_indexes) >= 2:
            title_index, artist_index = nonempty_indexes[:2]
            title = title or lines[title_index].strip()
            artist = artist or lines[artist_index].strip()
            metadata_indexes.update({title_index, artist_index})
        elif header_lines is None:
            auto_indexes = _auto_header_indexes(lines, raw_text)
            if auto_indexes:
                title_index, artist_index = auto_indexes
                title = title or lines[title_index].strip()
                artist = artist or lines[artist_index].strip()
                metadata_indexes.update(auto_indexes)

    if not title or not artist:
        for index, line in enumerate(lines):
            if index in metadata_indexes:
                continue
            combined = _combined_match(line)
            if not combined:
                continue
            fallback_title, fallback_artist = combined
            title = title or fallback_title
            artist = artist or fallback_artist
            metadata_indexes.add(index)
            if title and artist:
                break

    lyrics = "\n".join(
        line for index, line in enumerate(lines) if index not in metadata_indexes
    ).strip()
    return {"title": title, "artist": artist, "lyrics": lyrics}


def main():
    parser = argparse.ArgumentParser(
        description="Clean pasted lyric text locally and extract metadata."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出歌曲名、歌手和清洗后的歌词 JSON",
    )
    parser.add_argument(
        "--header-lines",
        type=int,
        choices=(0, 2),
        default=None,
        help="2=强制将前两个非空行按‘歌名、歌手’处理；0=关闭自动判断",
    )
    args = parser.parse_args()

    raw_text = sys.stdin.read()
    if not raw_text.strip():
        print("Error: 没有输入内容。请通过管道传入用户粘贴的文本。", file=sys.stderr)
        sys.exit(1)

    prepared = prepare_text(raw_text, header_lines=args.header_lines)
    if args.json:
        print(json.dumps(prepared, ensure_ascii=False, indent=2))
    else:
        print(prepared["lyrics"])


if __name__ == "__main__":
    main()
