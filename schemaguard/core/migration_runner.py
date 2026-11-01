"""
schemaguard/core/migration_runner.py
-------------------------------------
Executes a migration SQL script strictly against the sandbox database copy.

Design guarantees
~~~~~~~~~~~~~~~~~
- **Never accepts the original database path** — only a
  :class:`~schemaguard.core.sandbox.SandboxContext` or an explicit sandbox
  file path produced by :func:`~schemaguard.core.sandbox.create_sandbox`.
- Executes statements inside an **explicit transaction** (``BEGIN`` /
  ``COMMIT`` / ``ROLLBACK``); DDL and DML are both transactional in SQLite.
- On failure at statement *N*: rolls back, records the failure details,
  and signals that post-migration checks should be skipped.
- All connections are closed in ``finally`` blocks regardless of outcome.
- The :func:`~schemaguard.utils.sql_safety.install_authorizer` hardening
  callback is active for the entire execution window.

Public API
~~~~~~~~~~
- :func:`run_migration` — execute a script, return a :class:`MigrationRunResult`.
- :class:`StatementOutcome` — result of a single statement execution.
- :class:`MigrationRunResult` — aggregated result of a complete script run.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from schemaguard.config import SANDBOX_DIR
from schemaguard.core.analyzer import split_statements
from schemaguard.core.sandbox import SandboxContext
from schemaguard.utils.sql_safety import (
    SqlSafetyError,
    assert_foreign_keys_enabled,
    assert_statement_safe,
    install_authorizer,
    remove_authorizer,
)

# ---------------------------------------------------------------------------
# Sentinel – used to detect if a path belongs to the sandbox root
# ---------------------------------------------------------------------------

_SANDBOX_ROOT: Final[Path] = Path(SANDBOX_DIR).resolve()


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StatementOutcome:
    """Execution record for a single SQL statement.

    Attributes:
        index:         Zero-based position of this statement in the script.
        sql:           The raw statement text that was attempted.
        succeeded:     ``True`` if the statement executed without error.
        elapsed_ms:    Wall-clock execution time in milliseconds.
        error_type:    Exception class name on failure, empty string on success.
        error_message: Full SQLite or safety error message on failure.
        rows_affected: ``rowcount`` reported by the cursor (may be -1 for DDL).
    """

    index: int
    sql: str
    succeeded: bool
    elapsed_ms: float
    error_type: str = ""
    error_message: str = ""
    rows_affected: int = -1


@dataclass(frozen=True)
class MigrationRunResult:
    """Aggregated result of executing a migration script against the sandbox.

    Attributes:
        sandbox_db_path:   Absolute path to the sandbox database file.
        migration_sql:     The complete raw SQL script that was rehearsed.
        succeeded:         ``True`` if every statement executed successfully.
        statements:        Ordered tuple of per-statement outcomes.
        failed_index:      Zero-based index of the first failed statement,
                           or ``-1`` if all statements succeeded.
        failed_error:      Error message from the first failure, or ``""``.
        total_elapsed_ms:  Total wall-clock time for the complete run.
        post_checks_valid: ``False`` if migration failed (post-checks skipped).
        rollback_performed: ``True`` if the transaction was rolled back.
    """

    sandbox_db_path: str
    migration_sql: str
    succeeded: bool
    statements: tuple[StatementOutcome, ...] = field(default_factory=tuple)
    failed_index: int = -1
    failed_error: str = ""
    total_elapsed_ms: float = 0.0
    post_checks_valid: bool = True
    rollback_performed: bool = False

    def first_failure(self) -> StatementOutcome | None:
        """Return the first failed :class:`StatementOutcome`, or ``None``."""
        return next(
            (s for s in self.statements if not s.succeeded),
            None,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_sandbox_path(db_path: Path) -> bool:
    """Return ``True`` if *db_path* lives under the configured sandbox root."""
    try:
        db_path.resolve().relative_to(_SANDBOX_ROOT)
        return True
    except ValueError:
        return False


def _open_sandbox_connection(db_path: Path) -> sqlite3.Connection:
    """Open a writable connection to the sandbox DB with manual transaction control.

    ``isolation_level=None`` disables Python's implicit transaction handling
    so we can issue explicit ``BEGIN`` / ``COMMIT`` / ``ROLLBACK`` ourselves.
    """
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def _execute_one(
    conn: sqlite3.Connection,
    sql: str,
    index: int,
) -> StatementOutcome:
    """Execute a single statement and capture its outcome.

    The authorizer is active during this call, so prohibited operations will
    raise ``DatabaseError: not authorized``.

    Args:
        conn:  Open sandbox connection with authorizer installed.
        sql:   Single SQL statement text.
        index: Position of this statement in the script.

    Returns:
        A :class:`StatementOutcome` (succeeded or failed).
    """
    t0 = time.perf_counter()
    try:
        cursor = conn.execute(sql)
        elapsed = (time.perf_counter() - t0) * 1000.0
        return StatementOutcome(
            index=index,
            sql=sql,
            succeeded=True,
            elapsed_ms=round(elapsed, 3),
            rows_affected=cursor.rowcount,
        )
    except (sqlite3.DatabaseError, sqlite3.OperationalError, sqlite3.IntegrityError) as exc:
        elapsed = (time.perf_counter() - t0) * 1000.0
        return StatementOutcome(
            index=index,
            sql=sql,
            succeeded=False,
            elapsed_ms=round(elapsed, 3),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_migration(
    sandbox: SandboxContext | Path,
    migration_sql: str,
) -> MigrationRunResult:
    """Execute *migration_sql* exclusively against the sandbox database.

    Parameters
    ----------
    sandbox:
        Either a :class:`~schemaguard.core.sandbox.SandboxContext` (whose
        ``.sandbox_db`` is used) or an explicit :class:`~pathlib.Path` to
        a file that **must** reside inside the configured
        :data:`~schemaguard.config.SANDBOX_DIR` directory.  Passing the
        original source database path is rejected.
    migration_sql:
        The complete multi-statement SQL migration script.

    Returns
    -------
    MigrationRunResult
        Structured record of every statement outcome plus a top-level
        ``succeeded`` flag and ``post_checks_valid`` signal.

    Raises
    ------
    ValueError
        If *sandbox* is a path that does not live under the sandbox root —
        safeguards against accidentally targeting the original database.
    """
    # ------------------------------------------------------------------ #
    # 1. Resolve and guard the sandbox path
    # ------------------------------------------------------------------ #
    if isinstance(sandbox, SandboxContext):
        db_path = sandbox.sandbox_db.resolve()
    else:
        db_path = Path(sandbox).resolve()

    if not _is_sandbox_path(db_path):
        raise ValueError(
            f"Security policy violation: '{db_path}' does not reside inside "
            f"the sandbox root '{_SANDBOX_ROOT}'. "
            "run_migration() only accepts sandbox database paths."
        )

    # ------------------------------------------------------------------ #
    # 2. Split the script into individual statements
    # ------------------------------------------------------------------ #
    statements_sql = split_statements(migration_sql)

    if not statements_sql:
        return MigrationRunResult(
            sandbox_db_path=str(db_path),
            migration_sql=migration_sql,
            succeeded=True,
            statements=(),
            post_checks_valid=True,
        )

    # ------------------------------------------------------------------ #
    # 3. Open connection and install safety controls
    # ------------------------------------------------------------------ #
    conn: sqlite3.Connection | None = None
    outcomes: list[StatementOutcome] = []
    overall_t0 = time.perf_counter()

    try:
        conn = _open_sandbox_connection(db_path)
        install_authorizer(conn)
        assert_foreign_keys_enabled(conn)

        # ---------------------------------------------------------------- #
        # 4. Execute all statements inside an explicit transaction
        # ---------------------------------------------------------------- #
        conn.execute("BEGIN;")
        transaction_open = True

        for idx, stmt in enumerate(statements_sql):
            # 4a. Pre-execution static safety check
            try:
                assert_statement_safe(stmt)
            except SqlSafetyError as safety_exc:
                outcome = StatementOutcome(
                    index=idx,
                    sql=stmt,
                    succeeded=False,
                    elapsed_ms=0.0,
                    error_type="SqlSafetyError",
                    error_message=str(safety_exc),
                )
                outcomes.append(outcome)
                # Roll back and halt
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                transaction_open = False

                total_ms = round((time.perf_counter() - overall_t0) * 1000.0, 3)
                return MigrationRunResult(
                    sandbox_db_path=str(db_path),
                    migration_sql=migration_sql,
                    succeeded=False,
                    statements=tuple(outcomes),
                    failed_index=idx,
                    failed_error=str(safety_exc),
                    total_elapsed_ms=total_ms,
                    post_checks_valid=False,
                    rollback_performed=True,
                )

            # 4b. Execute the statement
            outcome = _execute_one(conn, stmt, idx)
            outcomes.append(outcome)

            if not outcome.succeeded:
                # Roll back immediately on first failure
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
                transaction_open = False

                total_ms = round((time.perf_counter() - overall_t0) * 1000.0, 3)
                return MigrationRunResult(
                    sandbox_db_path=str(db_path),
                    migration_sql=migration_sql,
                    succeeded=False,
                    statements=tuple(outcomes),
                    failed_index=idx,
                    failed_error=outcome.error_message,
                    total_elapsed_ms=total_ms,
                    post_checks_valid=False,
                    rollback_performed=True,
                )

        # ---------------------------------------------------------------- #
        # 5. Commit if all statements succeeded
        # ---------------------------------------------------------------- #
        if transaction_open:
            conn.execute("COMMIT;")
            transaction_open = False

        total_ms = round((time.perf_counter() - overall_t0) * 1000.0, 3)
        return MigrationRunResult(
            sandbox_db_path=str(db_path),
            migration_sql=migration_sql,
            succeeded=True,
            statements=tuple(outcomes),
            failed_index=-1,
            failed_error="",
            total_elapsed_ms=total_ms,
            post_checks_valid=True,
            rollback_performed=False,
        )

    finally:
        if conn is not None:
            # Safety net: roll back if we somehow exit with an open transaction
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass  # No open transaction — expected for the happy path
            remove_authorizer(conn)
            conn.close()

