"""
schemaguard/core/invariant_runner.py
-----------------------------------
Data invariant runner for post-migration sandbox database verification.

An invariant is a read-only SQL query asserting that no invalid or corrupt data
exists in the database (e.g. no negative order totals, no orphaned child records).

Evaluation Rule:
  - ZERO violating rows  -> PASS
  - >= 1 violating rows  -> FAIL (records exact count of violating rows)
  - Execution/SQL error  -> ERROR (never reports SQL errors as PASS)

Strict read-only enforcement:
  - AST check with SQLGlot dialect="sqlite" permits only SELECT queries.
  - SQLite authorizer strictly blocks any write/mutation operation.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Iterable

from schemaguard.config import SANDBOX_DIR
from schemaguard.core.contract_runner import (
    read_only_contract_authorizer,
    validate_read_only_ast,
)
from schemaguard.core.sandbox import SandboxContext
from schemaguard.models import InvariantResult, InvariantStatus

_SANDBOX_ROOT: Final[Path] = Path(SANDBOX_DIR).resolve()


# ---------------------------------------------------------------------------
# Invariant query specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvariantQuery:
    """Specification of an invariant assertion query.

    Attributes:
        name:        Human-readable name or title (e.g. "No negative order totals").
        sql:         Read-only SELECT query that identifies violating rows.
        description: Optional details about the invariant requirement.
    """

    name: str
    sql: str
    description: str = ""


# ---------------------------------------------------------------------------
# Path and Security Guards
# ---------------------------------------------------------------------------


def _is_sandbox_path(db_path: Path) -> bool:
    """Return True if db_path resides strictly within the configured sandbox root."""
    try:
        db_path.resolve().relative_to(_SANDBOX_ROOT)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------------------------


def _execute_invariant_query(
    conn: sqlite3.Connection,
    name: str,
    sql: str,
) -> InvariantResult:
    """Execute a single invariant query under strict read-only authorizer."""
    # 1. AST Read-only check
    is_safe, reject_reason = validate_read_only_ast(sql)
    if not is_safe:
        return InvariantResult(
            name=name,
            sql=sql,
            status=InvariantStatus.ERROR,
            violating_rows_count=0,
            error_message=f"Invariant AST validation rejected query: {reject_reason}",
            execution_time_ms=0.0,
        )

    # 2. Execute under authorizer protection
    conn.set_authorizer(read_only_contract_authorizer)
    t0 = time.perf_counter()

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        violating_count = len(rows)

        if violating_count == 0:
            return InvariantResult(
                name=name,
                sql=sql,
                status=InvariantStatus.PASS,
                violating_rows_count=0,
                error_message="",
                execution_time_ms=round(elapsed_ms, 3),
            )

        # Build sample violations from first few rows
        samples: list[dict[str, Any]] = []
        if cursor.description:
            col_names = [d[0] for d in cursor.description]
            for row in rows[:5]:
                samples.append(dict(zip(col_names, row)))

        return InvariantResult(
            name=name,
            sql=sql,
            status=InvariantStatus.FAIL,
            violating_rows_count=violating_count,
            error_message=f"Invariant violated: found {violating_count} violating row(s).",
            execution_time_ms=round(elapsed_ms, 3),
            sample_violations=tuple(samples),
        )

    except sqlite3.DatabaseError as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        err_msg = str(exc)
        if "not authorized" in err_msg.lower():
            err_msg = f"Security authorizer rejected operation: {err_msg}"
        return InvariantResult(
            name=name,
            sql=sql,
            status=InvariantStatus.ERROR,
            violating_rows_count=0,
            error_message=err_msg,
            execution_time_ms=round(elapsed_ms, 3),
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return InvariantResult(
            name=name,
            sql=sql,
            status=InvariantStatus.ERROR,
            violating_rows_count=0,
            error_message=str(exc),
            execution_time_ms=round(elapsed_ms, 3),
        )
    finally:
        conn.set_authorizer(None)


def _normalize_invariant(item: InvariantQuery | dict | tuple) -> InvariantQuery:
    """Normalize raw items into InvariantQuery objects."""
    if isinstance(item, InvariantQuery):
        return item
    if isinstance(item, dict):
        return InvariantQuery(
            name=item.get("name", item.get("invariant_name", "invariant")),
            sql=item.get("sql", item.get("query", "")),
            description=item.get("description", ""),
        )
    if isinstance(item, (tuple, list)):
        inv_name = str(item[0])
        inv_sql = str(item[1])
        inv_desc = str(item[2]) if len(item) > 2 else ""
        return InvariantQuery(name=inv_name, sql=inv_sql, description=inv_desc)

    raise TypeError(f"Unsupported invariant item type: {type(item).__name__}")


def run_invariant(
    sandbox: SandboxContext | sqlite3.Connection | Path | str,
    invariant: InvariantQuery | dict | tuple,
) -> InvariantResult:
    """Execute a single data invariant assertion against the sandbox database."""
    results = run_invariants(sandbox, [invariant])
    return results[0]


def run_invariants(
    sandbox: SandboxContext | sqlite3.Connection | Path | str,
    invariants: Iterable[InvariantQuery | dict | tuple],
) -> list[InvariantResult]:
    """Execute a collection of data invariants against the sandbox database.

    Runs all invariants independently without halting on errors.

    Args:
        sandbox: A SandboxContext, an open Connection, or a verified sandbox Path.
        invariants: Collection of InvariantQuery, dict, or tuple objects.

    Returns:
        List of InvariantResult instances.

    Raises:
        ValueError: If a filesystem path outside the sandbox root is supplied.
    """
    conn: sqlite3.Connection | None = None
    close_conn = False

    if isinstance(sandbox, sqlite3.Connection):
        conn = sandbox
    elif isinstance(sandbox, SandboxContext):
        db_path = sandbox.sandbox_db.resolve()
        conn = sqlite3.connect(str(db_path))
        close_conn = True
    else:
        db_path = Path(sandbox).resolve()
        if not _is_sandbox_path(db_path):
            raise ValueError(
                f"Security policy violation: '{db_path}' is not within sandbox root "
                f"'{_SANDBOX_ROOT}'. Invariants can only be run on sandbox copies."
            )
        conn = sqlite3.connect(str(db_path))
        close_conn = True

    try:
        results: list[InvariantResult] = []
        for raw_item in invariants:
            inv = _normalize_invariant(raw_item)
            res = _execute_invariant_query(conn=conn, name=inv.name, sql=inv.sql)
            results.append(res)
        return results
    finally:
        if close_conn and conn is not None:
            conn.close()


def parse_invariants_file(path_or_text: Path | str) -> list[InvariantQuery]:
    """Parse invariant queries from a SQL file or multi-line text.

    Extracts comments preceding SQL statements to use as the invariant's name.

    Args:
        path_or_text: Path to a .sql file or a string containing invariant statements.

    Returns:
        List of InvariantQuery objects.
    """
    raw_content: str
    if isinstance(path_or_text, Path) or (isinstance(path_or_text, str) and "\n" not in path_or_text and Path(path_or_text).is_file()):
        raw_content = Path(path_or_text).read_text(encoding="utf-8")
    else:
        raw_content = str(path_or_text)

    # Split by semicolon statements
    raw_chunks = [c.strip() for c in raw_content.split(";") if c.strip()]
    invariants: list[InvariantQuery] = []

    for idx, chunk in enumerate(raw_chunks):
        lines = chunk.strip().splitlines()
        comments: list[str] = []
        sql_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--"):
                # Clean comment text
                comment_text = stripped.lstrip("-").strip()
                if comment_text:
                    comments.append(comment_text)
            elif stripped:
                sql_lines.append(stripped)

        sql_text = " ".join(sql_lines).strip()
        if not sql_text:
            continue

        name = comments[0] if comments else f"invariant_{idx + 1}"
        description = " ".join(comments[1:]) if len(comments) > 1 else ""
        invariants.append(InvariantQuery(name=name, sql=sql_text, description=description))

    return invariants


__all__ = [
    "InvariantQuery",
    "InvariantStatus",
    "InvariantResult",
    "run_invariant",
    "run_invariants",
    "parse_invariants_file",
]

