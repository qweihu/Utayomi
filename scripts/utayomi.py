#!/usr/bin/env python3
"""Single in-memory Utayomi entry point.

The Agent supplies translations in memory when it uses ``process_lyrics``.
The command-line form is deterministic: it cleans and annotates user input,
then emits HTML by default or Markdown when explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from build_html import build_html
from prepare_lyrics import prepare_text
from utayomi_core import convert_to_ruby


DEFAULT_TITLE = "Untitled Song"
DEFAULT_ARTIST = "Unknown Artist"
MAX_AGENT_JSON_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class ProcessedLyrics:
    """A fully in-memory lyric document and its user-facing renderings."""

    title: str
    artist: str
    annotated: str
    pairs: tuple[tuple[str, str], ...]
    markdown: str
    html: str
    source: str | None = None


def _pairs(
    annotated: str,
    translations: Sequence[str] | None,
) -> tuple[tuple[str, str], ...]:
    source_lines = annotated.splitlines()
    while source_lines and not source_lines[-1].strip():
        source_lines.pop()
    lyric_count = sum(bool(line.strip()) for line in source_lines)
    if translations is not None:
        if len(translations) != lyric_count:
            raise ValueError(
                f"翻译行数与歌词行数不匹配：歌词 {lyric_count} 行，翻译 {len(translations)} 行"
            )
        if any(
            not isinstance(line, str) or "\n" in line or "\r" in line
            for line in translations
        ):
            raise ValueError("每条翻译必须是单独的一行文本")

    pairs = []
    translation_index = 0
    for line in source_lines:
        if not line.strip():
            pairs.append(("", ""))
            continue
        translation = (
            translations[translation_index].strip()
            if translations is not None
            else ""
        )
        pairs.append((line, translation))
        translation_index += 1
    return tuple(pairs)


def _to_markdown(title: str, artist: str, pairs: Sequence[tuple[str, str]]) -> str:
    blocks = [f"**{title} / {artist}**", ""]
    for japanese, translation in pairs:
        blocks.append(japanese)
        if translation:
            blocks.append(translation)
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def process_lyrics(
    raw_text: str,
    *,
    translations: Sequence[str] | None = None,
    mode: str = "hiragana",
    language: str = "und",
    title: str | None = None,
    artist: str | None = None,
    source: str | None = None,
) -> ProcessedLyrics:
    """Clean, annotate, pair and render lyrics without intermediate files."""

    if not raw_text.strip():
        raise ValueError("没有输入内容")
    explicit_metadata = title is not None or artist is not None
    prepared = prepare_text(
        raw_text,
        header_lines=0 if explicit_metadata else None,
    )
    lyrics = prepared["lyrics"]
    if not lyrics.strip():
        raise ValueError("清洗后没有可处理的歌词内容")

    annotated = convert_to_ruby(lyrics, mode=mode)
    title = (title or prepared["title"] or DEFAULT_TITLE).strip()
    artist = (artist or prepared["artist"] or DEFAULT_ARTIST).strip()
    source = source.strip() if source and source.strip() else None
    pairs = _pairs(annotated, translations)
    markdown = _to_markdown(title, artist, pairs)
    html = build_html(title, artist, list(pairs), language=language, source=source)
    return ProcessedLyrics(
        title=title,
        artist=artist,
        annotated=annotated,
        pairs=pairs,
        markdown=markdown,
        html=html,
        source=source,
    )


def _read_agent_payload() -> dict:
    raw = sys.stdin.read(MAX_AGENT_JSON_BYTES + 1)
    if len(raw.encode("utf-8")) > MAX_AGENT_JSON_BYTES:
        raise ValueError("Agent JSON exceeds the 2 MiB limit")

    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")

    try:
        payload = json.loads(raw, parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Agent JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Agent input must be a JSON object")
    return payload


def _agent_response(payload: dict) -> dict:
    action = payload.get("action")
    if not isinstance(action, str) or action not in {"prepare", "render"}:
        raise ValueError("action must be 'prepare' or 'render'")
    raw_text = payload.get("text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("text must be a non-empty string")

    for field in ("title", "artist", "source", "language", "mode", "format"):
        if (
            field in payload
            and payload[field] is not None
            and not isinstance(payload[field], str)
        ):
            raise ValueError(f"{field} must be a string")
    title = payload.get("title")
    artist = payload.get("artist")
    source = payload.get("source")
    mode = payload.get("mode") or "hiragana"
    language = payload.get("language") or "und"

    if action == "prepare":
        prepared = prepare_text(
            raw_text,
            header_lines=0 if title is not None or artist is not None else None,
        )
        lyrics = prepared["lyrics"]
        if not lyrics.strip():
            raise ValueError("清洗后没有可处理的歌词内容")
        annotated = convert_to_ruby(lyrics, mode=mode)
        source_lines = lyrics.split("\n")
        annotated_lines = annotated.split("\n")
        if len(source_lines) != len(annotated_lines):
            raise RuntimeError("注音结果没有保留歌词行结构")
        output_title = (title or prepared["title"] or DEFAULT_TITLE).strip()
        output_artist = (artist or prepared["artist"] or DEFAULT_ARTIST).strip()
        return {
            "action": "prepared",
            "title": output_title,
            "artist": output_artist,
            "source": source.strip() if source and source.strip() else None,
            "lyrics": lyrics,
            "lines": [
                {"text": source_line, "annotated": annotated_line}
                for source_line, annotated_line in zip(
                    source_lines, annotated_lines, strict=True
                )
            ],
            "translation_line_count": sum(
                bool(line.strip()) for line in source_lines
            ),
        }

    translations = payload.get("translations")
    if translations is not None and (
        not isinstance(translations, list)
        or any(not isinstance(line, str) for line in translations)
    ):
        raise ValueError("translations must be a list of strings or null")
    output_format = payload.get("format") or "html"
    if output_format not in {"html", "markdown"}:
        raise ValueError("format must be 'html' or 'markdown'")
    document = process_lyrics(
        raw_text,
        translations=translations,
        mode=mode,
        language=language,
        title=title,
        artist=artist,
        source=source,
    )
    return {
        "action": "rendered",
        "format": output_format,
        "title": document.title,
        "artist": document.artist,
        "source": document.source,
        "content": document.html if output_format == "html" else document.markdown,
    }

def _next_target(source: Path, suffix: str) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    target = source.with_name(f"{source.stem}.{stamp}{suffix}")
    counter = 2
    while target.exists():
        target = source.with_name(f"{source.stem}.{stamp}-{counter}{suffix}")
        counter += 1
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="utayomi",
        description="清洗并注音用户提供的日语歌词；默认输出独立 HTML。",
    )
    parser.add_argument(
        "--file", type=Path, help="从文件读取；结果写入同目录的时间戳文件"
    )
    parser.add_argument("--romaji", action="store_true", help="明确要求时使用罗马音")
    parser.add_argument("--markdown", action="store_true", help="明确要求时输出 Markdown")
    parser.add_argument("--language", default="und", help=argparse.SUPPRESS)
    parser.add_argument(
        "--agent-json",
        action="store_true",
        help="read a prepare/render JSON request from stdin and return JSON",
    )
    args = parser.parse_args(argv)

    try:
        if args.agent_json:
            if args.file or args.romaji or args.markdown:
                raise ValueError(
                    "--agent-json cannot be combined with file or format flags"
                )
            response = _agent_response(_read_agent_payload())
            json.dump(
                response, sys.stdout, ensure_ascii=False, indent=2, allow_nan=False
            )
            sys.stdout.write("\n")
            return 0

        source_path = args.file.expanduser().resolve() if args.file else None
        raw_text = (
            source_path.read_text(encoding="utf-8")
            if source_path
            else sys.stdin.read()
        )
        document = process_lyrics(
            raw_text,
            mode="romaji" if args.romaji else "hiragana",
            language=args.language,
        )
        content = document.markdown if args.markdown else document.html
        if source_path:
            target = _next_target(source_path, ".md" if args.markdown else ".html")
            target.write_text(content, encoding="utf-8")
            print(f"处理完成！已保存：{target}", file=sys.stderr)
        else:
            sys.stdout.write(content)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"utayomi: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
