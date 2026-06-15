from __future__ import annotations

import tomllib
from pathlib import Path

from setuptools import setup

with Path(__file__).with_name("pyproject.toml").open("rb") as _f:
    _version = tomllib.load(_f)["project"]["version"]

setup(
    extras_require={
        "dev": [
            "duckdb>=0.6",
            "sqlglot-mypy >= 2.1.0.post3; python_version >= '3.10'",
            "mypy; python_version < '3.10'",
            "pandas",
            "pandas-stubs",
            "python-dateutil",
            "pytz",
            "pdoc",
            "pre-commit",
            "ruff==0.15.6",
            "types-python-dateutil",
            "types-pytz",
            "typing_extensions",
            "pyperf",
        ],
        "c": [f"sqlglotc=={_version}; python_version >= '3.10'"],
        "rs": ["sqlglotrs==0.13.0", f"sqlglotc=={_version}; python_version >= '3.10'"],
    },
)
