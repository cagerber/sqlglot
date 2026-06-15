#!/usr/bin/env python3
"""Sync sqlglot/_version.py from [project].version in pyproject.toml (Trifour fork)."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
VERSION_PY = ROOT / "sqlglot" / "_version.py"


def _version_tuple(version: str) -> tuple[int | str, ...]:
    base, _, local = version.partition("+")
    parts: list[int | str] = [int(x) for x in base.split(".")]
    if local:
        for piece in re.split(r"[.-]", local):
            parts.append(int(piece) if piece.isdigit() else piece)
    return tuple(parts)


def main() -> int:
    with PYPROJECT.open("rb") as f:
        version = tomllib.load(f)["project"]["version"]
    tup = _version_tuple(version)
    VERSION_PY.write_text(
        f'''# Trifour fork: committed static version (upstream uses setuptools-scm + gitignore).
from __future__ import annotations

__all__ = [
    "__version__",
    "__version_tuple__",
    "version",
    "version_tuple",
    "__commit_id__",
    "commit_id",
]

version: str
__version__: str
__version_tuple__: tuple[int | str, ...]
version_tuple: tuple[int | str, ...]
commit_id: str | None
__commit_id__: str | None

__version__ = version = "{version}"
__version_tuple__ = version_tuple = {tup!r}

__commit_id__ = commit_id = None
''',
        encoding="utf-8",
    )
    print(f"Wrote {VERSION_PY.relative_to(ROOT)} for {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
