#!/usr/bin/env python3
"""Safely save Agent-produced Markdown after the user confirms its path.

The script deliberately requires an absolute output path. It never invents a
directory or overwrites an existing file unless the caller explicitly passes
``--overwrite``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def save_text(
    content: str,
    output: Path,
    *,
    overwrite: bool = False,
    create_parent: bool = False,
) -> Path:
    """Write ``content`` to a confirmed absolute path and return that path."""

    if not output.is_absolute():
        raise ValueError("输出路径必须是用户确认的绝对路径")
    if not content:
        raise ValueError("不能保存空的 Markdown 内容")

    parent = output.parent
    if not parent.is_dir():
        if not create_parent:
            raise FileNotFoundError(
                f"输出目录不存在: {parent}；确认目录后重试，或加 --create-parent"
            )
        parent.mkdir(parents=True, exist_ok=True)

    flags = os.O_WRONLY | os.O_CREAT
    flags |= os.O_TRUNC if overwrite else os.O_EXCL
    try:
        file_descriptor = os.open(output, flags, 0o644)
    except FileExistsError as exc:
        raise FileExistsError(
            f"输出文件已存在，为避免覆盖请换路径或加 --overwrite: {output}"
        ) from exc

    with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="保存用户确认路径下的 Utayomi Markdown 结果"
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="用户确认的绝对输出路径",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="从文件读取 Markdown；不提供时从标准输入读取",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="明确允许覆盖已有文件",
    )
    parser.add_argument(
        "--create-parent",
        action="store_true",
        help="明确允许创建不存在的父目录",
    )
    args = parser.parse_args(argv)

    try:
        content = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        target = save_text(
            content,
            args.output,
            overwrite=args.overwrite,
            create_parent=args.create_parent,
        )
    except (OSError, ValueError) as exc:
        print(f"utayomi: {exc}", file=sys.stderr)
        return 2

    print(f"处理完成！歌词已保存：{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
