"""
schemaguard/utils/sql_safety.py
--------------------------------
Security enforcement layer for sandbox connections.

Provides two complementary mechanisms:

1. **set_authorizer callback** — installed on a live SQLite connection to
   intercept and DENY high-risk administrative operations at the engine level
   before any SQL executes.

2. **Static deny-list check** — a pre-execution regex scan that catches
   ``PRAGMA writable_schema`` and similar threats that the authorizer callback
   may not intercept until a statement is partially evaluated.

Denied operations
~~~~~~~~~~~~~~~~~
- ``SQLITE_ATTACH``  — prevents attaching external databases.
- ``SQLITE_DETACH``  — prevents detaching databases.
- ``PRAGMA writable_schema``   — would allow direct schema tampering.
- ``PRAGMA wal_checkpoint``    — administrative WAL control.
- ``PRAGMA integrity_check``   — allowed (read-only diagnostic).
- ``enable_load_extension``    — not reachable via SQL; documented here for
  completeness.  Extension loading is never called on sandbox connections.

Allowed operations
~~~~~~~~~~~~~~~~~~
All normal DDL (CREATE, ALTER, DROP), DML (INSERT, UPDATE, DELETE, SELECT)
and safe pragmas (foreign_keys, journal_mode, busy_timeout, quick_check,
table_info, index_list, etc.) are permitted.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Final

# ---------------------------------------------------------------------------
# Blocked PRAGMA names (case-insensitive exact match)
# ---------------------------------------------------------------------------

_BLOCKED_PRAGMAS: Final[frozenset[str]] = frozenset(
    {
        "writable_schema",
        "wal_checkpoint",
        "optimize",            # can rewrite indexes across attached DBs
        "wal_autocheckpoint",  # WAL config – no place in migration scripts
        "page_size",           # can corrupt DB if changed at wrong time
        "auto_vacuum",         # structural change not part of migration intent
        "shrink_memory",       # session-global side-effect
    }
)

# Regex matching DETACH and ATTACH keywords at statement level (pre-parse guard)
_ATTACH_DETACH_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(ATTACH|DETACH)\b", re.IGNORECASE
)

# Regex matching writable_schema pragma (pre-parse guard)
_WRITABLE_SCHEMA_RE: Final[re.Pattern[str]] = re.compile(
    r"\bPRAGMA\s+writable_schema\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class SqlSafetyError(Exception):
    """Raised when a statement violates sandbox security policy."""


# ---------------------------------------------------------------------------
# Authorizer callback
# ---------------------------------------------------------------------------


def _sandbox_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    db_name: str | None,
    trigger_name: str | None,
) -> int:
    """SQLite authorizer callback enforcing sandbox security policy.

    Called by the SQLite engine for every operation attempted on a connection.
    Returns ``SQLITE_DENY`` to reject the operation, ``SQLITE_OK`` to allow.

    Designed to be installed via ``conn.set_authorizer(_sandbox_authorizer)``.

    Args:
        action:       SQLite action code (e.g. ``SQLITE_ATTACH``).
        arg1:         First context argument (varies by action).
        arg2:         Second context argument (varies by action).
        db_name:      Database name or ``None``.
        trigger_name: Trigger name or ``None``.

    Returns:
        ``SQLITE_DENY`` (1) or ``SQLITE_OK`` (0).
    """
    if action == sqlite3.SQLITE_ATTACH:
        return sqlite3.SQLITE_DENY

    if action == sqlite3.SQLITE_DETACH:
        return sqlite3.SQLITE_DENY

    if action == sqlite3.SQLITE_PRAGMA:
        pragma_name = (arg1 or "").strip().lower()
        if pragma_name in _BLOCKED_PRAGMAS:
            return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


# ---------------------------------------------------------------------------
# Pre-execution static deny-list check
# ---------------------------------------------------------------------------


def assert_statement_safe(sql: str) -> None:
    """Check *sql* against the static deny-list before execution.

    This is a lightweight defence-in-depth guard that runs before the
    authorizer callback gets a chance to fire, catching obvious violations
    early with a descriptive error rather than a generic authorizer error.

    Args:
        sql: Single SQL statement string (without surrounding whitespace).

    Raises:
        SqlSafetyError: If the statement matches a blocked pattern.
    """
    stripped = sql.strip()

    if _ATTACH_DETACH_RE.match(stripped):
        keyword = stripped.split()[0].upper()
        raise SqlSafetyError(
            f"{keyword} is not permitted in sandbox migrations. "
            "Attaching or detaching databases is a security risk."
        )

    if _WRITABLE_SCHEMA_RE.search(stripped):
        raise SqlSafetyError(
            "PRAGMA writable_schema is not permitted in sandbox migrations. "
            "Directly modifying the sqlite_schema table bypasses all safety checks."
        )


# ---------------------------------------------------------------------------
# Connection hardening
# ---------------------------------------------------------------------------


def install_authorizer(conn: sqlite3.Connection) -> None:
    """Install the sandbox authorizer callback on *conn*.

    Call this immediately after opening a sandbox connection and before
    executing any migration SQL.

    Args:
        conn: An open :class:`sqlite3.Connection` to harden.
    """
    conn.set_authorizer(_sandbox_authorizer)


def remove_authorizer(conn: sqlite3.Connection) -> None:
    """Remove the authorizer from *conn* (restores default permissive mode).

    Needed when the same connection is later used for read-back queries
    that require pragmas blocked by the sandbox policy (e.g. during
    :func:`~schemaguard.core.schema_inspector.inspect_schema`).

    Args:
        conn: An open :class:`sqlite3.Connection`.
    """
    conn.set_authorizer(None)


def assert_foreign_keys_enabled(conn: sqlite3.Connection) -> None:
    """Assert that ``PRAGMA foreign_keys`` is currently ON.

    Raises:
        RuntimeError: If foreign keys are not enabled on *conn*.
    """
    row = conn.execute("PRAGMA foreign_keys;").fetchone()
    enabled = row[0] if row else 0
    if not enabled:
        raise RuntimeError(
            "Foreign key enforcement is disabled on this connection. "
            "Set PRAGMA foreign_keys = ON; before running migrations."
        )

