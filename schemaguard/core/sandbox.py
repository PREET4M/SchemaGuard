"""
schemaguard/core/sandbox.py
---------------------------
Isolated sandbox lifecycle for migration rehearsal.

The sandbox:
1. Opens the source database **strictly read-only** (``?mode=ro``).
2. Creates a unique temporary directory under :data:`~schemaguard.config.SANDBOX_DIR`.
3. Copies the database using SQLite's online-backup API — safer than
   ``shutil.copy`` because it produces a consistent snapshot even if the
   source has active writers.
4. Returns a :class:`SandboxContext` handle the caller uses to obtain a
   writable connection to the copy.
5. Cleans up the temporary directory when requested (or on error).

**Guarantee**: the original database is never opened in a writable mode,
and the caller never controls the destination path.

Public API
~~~~~~~~~~
- :func:`create_sandbox` — create an isolated copy, return a context handle.
- :class:`SandboxContext` — lightweight handle with ``.connect()`` / ``.cleanup()``.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from shutil import rmtree

from schemaguard.config import SANDBOX_DB_FILENAME, SANDBOX_DIR, SANDBOX_PRAGMAS
from schemaguard.utils.file_validation import validate_sqlite_file


# ---------------------------------------------------------------------------
# Sandbox context handle
# ---------------------------------------------------------------------------


@dataclass
class SandboxContext:
    """Handle representing an active sandbox.

    Attributes:
        source_path:  Resolved path to the **original** (read-only) database.
        sandbox_dir:  Path to the unique temporary directory holding the copy.
        sandbox_db:   Path to the sandboxed database file inside *sandbox_dir*.
    """

    source_path: Path
    sandbox_dir: Path
    sandbox_db: Path
    _connections: list[sqlite3.Connection] = field(
        default_factory=list, repr=False
    )

    def connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        """Open a connection to the sandboxed database copy.

        Args:
            readonly: If ``True``, open in read-only URI mode.

        Returns:
            An open :class:`sqlite3.Connection` that is tracked for cleanup.
        """
        if readonly:
            uri = f"file:{self.sandbox_db.as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(self.sandbox_db)

        # Apply configured pragmas.
        # Skip write-mode pragmas (e.g. journal_mode) for read-only connections.
        _WRITE_PRAGMAS = frozenset({"journal_mode"})
        for pragma, value in SANDBOX_PRAGMAS.items():
            if readonly and pragma in _WRITE_PRAGMAS:
                continue
            conn.execute(f"PRAGMA {pragma} = {value};")

        self._connections.append(conn)
        return conn

    def cleanup(self) -> None:
        """Close all tracked connections and remove the sandbox directory.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        for conn in self._connections:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
        self._connections.clear()

        if self.sandbox_dir.exists():
            rmtree(self.sandbox_dir, ignore_errors=True)

    @property
    def is_alive(self) -> bool:
        """Return ``True`` if the sandbox directory still exists on disk."""
        return self.sandbox_dir.exists()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _open_source_readonly(source_path: Path) -> sqlite3.Connection:
    """Open the source database in strict read-only mode via URI.

    Raises :class:`sqlite3.OperationalError` if the file cannot be opened.
    """
    uri = f"file:{source_path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _make_sandbox_dir() -> Path:
    """Create a unique temporary directory under :data:`SANDBOX_DIR`.

    The directory name includes a UUID4 fragment to avoid collisions when
    multiple rehearsals run concurrently.
    """
    root = Path(SANDBOX_DIR)
    root.mkdir(parents=True, exist_ok=True)
    unique_name = f"run_{uuid.uuid4().hex[:12]}"
    sandbox = root / unique_name
    sandbox.mkdir()
    return sandbox


def _backup_database(
    source_conn: sqlite3.Connection,
    target_path: Path,
) -> None:
    """Copy the source database to *target_path* using the backup API.

    This produces a consistent, point-in-time snapshot of the source even
    if other connections are writing to it concurrently.
    """
    target_conn = sqlite3.connect(target_path)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_sandbox(
    source_path: Path | str,
    *,
    max_size_bytes: int | None = None,
) -> SandboxContext:
    """Create an isolated sandbox copy of the source database.

    Steps:
    1. Validate that *source_path* is a genuine SQLite file.
    2. Open the source in read-only mode.
    3. Create a unique temporary directory.
    4. Copy the database using the SQLite backup API.
    5. Return a :class:`SandboxContext` handle.

    Args:
        source_path:    Path to the original database.
        max_size_bytes: Optional override for the file-size limit.

    Returns:
        A :class:`SandboxContext` pointing to the sandboxed copy.

    Raises:
        FileValidationError: If the source file is invalid.
        sqlite3.OperationalError: If the backup fails.
    """
    validate_kwargs: dict = {}
    if max_size_bytes is not None:
        validate_kwargs["max_size_bytes"] = max_size_bytes

    resolved_source = validate_sqlite_file(source_path, **validate_kwargs)

    sandbox_dir = _make_sandbox_dir()
    sandbox_db = sandbox_dir / SANDBOX_DB_FILENAME

    source_conn = _open_source_readonly(resolved_source)
    try:
        _backup_database(source_conn, sandbox_db)
    except Exception:
        # If backup fails, clean up the sandbox dir we just created.
        rmtree(sandbox_dir, ignore_errors=True)
        raise
    finally:
        source_conn.close()

    return SandboxContext(
        source_path=resolved_source,
        sandbox_dir=sandbox_dir,
        sandbox_db=sandbox_db,
    )
