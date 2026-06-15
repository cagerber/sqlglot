# Trifour fork: committed static version (upstream uses setuptools-scm + gitignore).
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

__version__ = version = "30.11.0+trifour.1"
__version_tuple__ = version_tuple = (30, 11, 0, 'trifour', 1)

__commit_id__ = commit_id = None
