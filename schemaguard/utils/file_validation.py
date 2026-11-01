"""
schemaguard/utils/file_validation.py
------------------------------------
Validates that a candidate file is an existing, reasonably-sized, genuine
SQLite database — not just a file whose name ends in ``.db``.

Public API
~~~~~~~~~~
- :func:`validate_sqlite_file` — single entry-point, raises on any problem.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from schemaguard.config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB

# The first 16 bytes of every valid SQLite database file.
# See https://www.sqlite.org/fileformat.html §1.2
_SQLITE_HEADER_MAGIC: bytes = b"SQLite format 3\x00"
_SQLITE_HEADER_LEN: int = len(_SQLITE_HEADER_MAGIC)  # 16

# Extensions we consider plausible for SQLite files.  Used only for
# user-friendly warnings — the real check is the header + PRAGMA.
VALID_EXTENSIONS: frozenset[str] = frozenset({".db", ".sqlite", ".sqlite3"})


class FileValidationError(Exception):
    """Raised when a candidate file fails any validation gate."""


# ---------------------------------------------------------------------------
# Individual checks (private)
# ---------------------------------------------------------------------------


def _check_exists(path: Path) -> None:
    """Raise if *path* does not point to an existing regular file."""
    if not path.exists():
        raise FileValidationError(f"File does not exist: {path}")
    if not path.is_file():
        raise FileValidationError(f"Path is not a regular file: {path}")


def _check_size(path: Path, max_bytes: int) -> None:
    """Raise if the file exceeds *max_bytes*."""
    size = path.stat().st_size
    if size == 0:
        raise FileValidationError(f"File is empty (0 bytes): {path}")
    if size > max_bytes:
        size_mb = size / (1024 * 1024)
        raise FileValidationError(
            f"File too large: {size_mb:.1f} MB exceeds the "
            f"{max_bytes / (1024 * 1024):.0f} MB limit."
        )


def _check_sqlite_header(path: Path) -> None:
    """Raise if the file's first 16 bytes are not the SQLite magic string."""
    with open(path, "rb") as fh:
        header = fh.read(_SQLITE_HEADER_LEN)
    if header != _SQLITE_HEADER_MAGIC:
        raise FileValidationError(
            f"File does not have a valid SQLite header: {path}"
        )


def _check_sqlite_readable(path: Path) -> None:
    """Open the file as a SQLite database and run ``PRAGMA quick_check``.

    Opens in read-only URI mode so the original is never mutated.
    """
    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError as exc:
        raise FileValidationError(
            f"Cannot open file as SQLite database: {exc}"
        ) from exc

    try:
        result = conn.execute("PRAGMA quick_check;").fetchone()
        if result is None or result[0] != "ok":
            detail = result[0] if result else "no response"
            raise FileValidationError(
                f"PRAGMA quick_check failed: {detail}"
            )
    except sqlite3.DatabaseError as exc:
        raise FileValidationError(
            f"File is not a valid SQLite database: {exc}"
        ) from exc
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_sqlite_file(
    path: Path | str,
    *,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> Path:
    """Validate that *path* is an existing, genuine, reasonably-sized SQLite DB.

    Checks run in order of cheapest-first:

    1. File exists and is a regular file.
    2. File size is > 0 and ≤ *max_size_bytes*.
    3. First 16 bytes match the SQLite header magic.
    4. ``PRAGMA quick_check`` succeeds via a read-only connection.

    Args:
        path: Filesystem path to the candidate file.
        max_size_bytes: Upper file-size limit in bytes.
            Defaults to :data:`~schemaguard.config.MAX_UPLOAD_SIZE_BYTES`.

    Returns:
        The resolved :class:`~pathlib.Path` on success.

    Raises:
        FileValidationError: If any check fails.
    """
    resolved = Path(path).resolve()
    _check_exists(resolved)
    _check_size(resolved, max_size_bytes)
    _check_sqlite_header(resolved)
    _check_sqlite_readable(resolved)
    return resolved

