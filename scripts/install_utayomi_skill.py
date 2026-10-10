#!/usr/bin/env python3
"""Install the Utayomi Skill and its small runtime into a Codex skills directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_ITEMS = ("SKILL.md", "PROMPT.md", "agents", "requirements.txt")
MIN_PYTHON = (3, 10)
RUNTIME_SCRIPTS = (
    "utayomi.py",
    "utayomi_core.py",
    "prepare_lyrics.py",
    "build_html.py",
)


def default_destination() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "skills" / "utayomi"


def _copy_item(source: Path, target: Path, *, force: bool) -> None:
    if source.is_dir():
        if target.exists() and force:
            shutil.rmtree(target)
        shutil.copytree(source, target, dirs_exist_ok=force)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def install(destination: Path, *, force: bool) -> Path:
    missing = [item for item in SKILL_ITEMS if not (ROOT / item).exists()]
    if missing:
        raise RuntimeError(f"项目 Skill 不完整，缺少: {', '.join(missing)}")
    missing_runtime = [
        item for item in RUNTIME_SCRIPTS if not (ROOT / "scripts" / item).is_file()
    ]
    if missing_runtime:
        raise RuntimeError(f"运行入口不完整，缺少: {', '.join(missing_runtime)}")

    destination = destination.expanduser().resolve()
    if destination.exists() and not force:
        raise RuntimeError(f"目标已存在，为避免覆盖请加 --force: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for item in SKILL_ITEMS:
        _copy_item(ROOT / item, destination / item, force=force)
    runtime_target = destination / "scripts"
    if runtime_target.exists() and force:
        shutil.rmtree(runtime_target)
    runtime_target.mkdir(parents=True, exist_ok=True)
    for item in RUNTIME_SCRIPTS:
        shutil.copy2(ROOT / "scripts" / item, runtime_target / item)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装 Utayomi Codex Skill")
    parser.add_argument("--destination", type=Path, help="安装目标目录")
    parser.add_argument("--force", action="store_true", help="允许更新已有安装")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < MIN_PYTHON:
            raise RuntimeError("Utayomi 需要 Python 3.10 或更高版本")
        target = install(args.destination or default_destination(), force=args.force)
    except (OSError, RuntimeError) as exc:
        print(f"install_utayomi_skill: {exc}", file=sys.stderr)
        return 2
    print(f"Utayomi Skill 已安装：{target}")
    print("安装目录包含 SKILL.md、PROMPT.md 和统一运行入口 scripts/utayomi.py。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
