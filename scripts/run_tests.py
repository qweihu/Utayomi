#!/usr/bin/env python3
"""Run the Python test suite with the best local project interpreter."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def candidate_interpreters() -> list[Path]:
    candidates = []
    configured = os.environ.get("UTAYOMI_PYTHON")
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(PROJECT_ROOT / ".venv" / "bin" / "python")
    system_python = shutil.which("python3")
    if system_python:
        candidates.append(Path(system_python))
    return candidates


def has_runtime_dependencies(candidate: Path) -> bool:
    probe = subprocess.run(
        [str(candidate), "-c", "import fugashi, pykakasi"],
        capture_output=True,
        text=True,
    )
    return probe.returncode == 0


def main() -> int:
    current = Path(sys.executable).resolve()
    if has_runtime_dependencies(current):
        os.chdir(PROJECT_ROOT)
        return subprocess.run(
            [str(current), "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=PROJECT_ROOT,
            check=False,
        ).returncode

    for candidate in candidate_interpreters():
        if (
            not candidate.is_file()
            or candidate.resolve() == current
            or not has_runtime_dependencies(candidate)
        ):
            continue
        os.chdir(PROJECT_ROOT)
        os.execv(
            str(candidate),
            [
                str(candidate),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ],
        )

    os.chdir(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=PROJECT_ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
