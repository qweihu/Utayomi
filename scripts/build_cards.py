#!/usr/bin/env python3
"""Build Anki mining cards from lyrics using japanese-language-core.

Input: cleaned lyrics text plus optional paired translation lines and an
optional Yomitan dictionary. Output: mining TSV or AnkiConnect payload JSON.

Examples:
    cat cleaned-lyrics.txt | .venv/bin/python scripts/build_cards.py --format tsv
    .venv/bin/python scripts/build_cards.py --input lyrics.txt \
      --translation translations.txt --dictionary JMdict.zip \
      --format payload --deck "Lyrics" --model "Basic"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from japanese_language_core.dictionary import YomitanDictionary
from japanese_language_core.dictionary.pitch import classify
from japanese_language_core.export import (
    MiningUnit,
    mining_payload,
    mining_tsv,
)
from japanese_language_core.reading import create_engine, count_mora, is_kanji


def _read_lines(path: str | None) -> list[str]:
    if path in (None, "-"):
        return sys.stdin.read().splitlines()
    return Path(path).read_text(encoding="utf-8").splitlines()


def _pick_expression(tokens) -> tuple[str, str]:
    for token in tokens:
        if any(is_kanji(char) for char in token.orig):
            return token.orig, token.hira
    for token in tokens:
        if token.orig.strip():
            return token.orig, token.hira
    return "", ""


def _enrich(expression: str, dictionary) -> tuple[str, str]:
    if dictionary is None or not expression:
        return "", ""
    entries = dictionary.lookup_terms(expression)
    if not entries:
        return "", ""
    entry = entries[0]
    pitch = ""
    if entry.pitch_accents and entry.reading:
        mora = count_mora(entry.reading)
        pitch = classify(mora, entry.pitch_accents[0].position)
    frequency = (
        str(entry.frequency.value)
        if entry.frequency and entry.frequency.value is not None
        else ""
    )
    return pitch, frequency


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="清洗后的歌词文本文件（- 表示 stdin）")
    parser.add_argument("--translation", help="逐行中文翻译文件（可选）")
    parser.add_argument("--dictionary", help="Yomitan 词典 zip（可选，补充声调/频率）")
    parser.add_argument("--format", choices=("tsv", "payload"), default="tsv")
    parser.add_argument("--deck", default="Lyrics")
    parser.add_argument("--model", default="Basic")
    parser.add_argument("--output", help="输出文件（默认 stdout）")
    args = parser.parse_args(argv)

    lyrics = [line for line in _read_lines(args.input) if line.strip()]
    translations = _read_lines(args.translation) if args.translation else []
    dictionary = (
        YomitanDictionary(args.dictionary) if args.dictionary else None
    )
    engine = create_engine("auto")

    units: list[MiningUnit] = []
    for index, line in enumerate(lyrics):
        tokens = tuple(engine.tokens(line))
        surface = "".join(token.orig for token in tokens)
        expression, reading = _pick_expression(tokens)
        pitch, frequency = _enrich(expression, dictionary)
        translation = (
            translations[index].strip()
            if index < len(translations) and translations[index].strip()
            else ""
        )
        units.append(
            MiningUnit(
                sentence=surface,
                translation=translation,
                expression=expression,
                reading=reading,
                pitch=pitch,
                frequency=frequency,
                tags=["lyrics"],
            )
        )

    if args.format == "payload":
        output = json.dumps(
            mining_payload(units, deck_name=args.deck, model_name=args.model),
            ensure_ascii=False,
            indent=2,
        )
    else:
        output = mining_tsv(units)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"卡片已写入：{args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
