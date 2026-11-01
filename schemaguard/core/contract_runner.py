"""
schemaguard/core/contract_runner.py
----------------------------------
Application query contract verification engine for post-migration databases.

Contracts are read-only SELECT queries replayed against the sandboxed SQLite
database to verify that existing (OLD_APP) or new (NEW_APP) queries remain
syntactically, structurally, and functionally compatible with the migrated schema.

Strict read-only enforcement:
1. SQLGlot AST inspection allows only SELECT and safe WITH...SELECT queries.
2. SQLite authorizer (set_authorizer) strictly blocks any mutating operations
   (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, ATTACH, DETACH, PRAGMAs).
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable

import sqlglot
from sqlglot import exp

from schemaguard.config import SANDBOX_DIR
from schemaguard.core.sandbox import SandboxContext
from schemaguard.models import CheckStatus, ContractResult, ContractStatus, ContractType

# ---------------------------------------------------------------------------
# Constants and Safety Sentinel
# ---------------------------------------------------------------------------

_SANDBOX_ROOT: Final[Path] = Path(SANDBOX_DIR).resolve()

# Permitted root query AST nodes
_ALLOWED_ROOT_NODES: Final[tuple[type[exp.Expression], ...]] = (
    exp.Select,
    exp.Union,
    exp.Intersect,
    exp.Except,
)

# Mutating or administrative AST nodes strictly forbidden in contracts
_DISALLOWED_AST_NODES: Final[tuple[type[exp.Expression], ...]] = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Command,
    exp.Pragma,
)

# SQLite authorizer actions permitted during contract execution
_READ_ONLY_ACTIONS: Final[frozenset[int]] = frozenset(
    {
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    }
)

_ATTACH_DETACH_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*(ATTACH|DETACH)\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Contract query input specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContractQuery:
    """A named application query contract specification.

    Attributes:
        name:          Identifier for the contract query (e.g. "old_app_users").
        sql:           The SQL SELECT statement string.
        contract_type: OLD_APP or NEW_APP.
    """

    name: str
    sql: str
    contract_type: ContractType | str = ContractType.OLD_APP


# ---------------------------------------------------------------------------
# Security Helpers
# ---------------------------------------------------------------------------


def _is_sandbox_path(db_path: Path) -> bool:
    """Return True if db_path resides strictly inside the configured sandbox root."""
    try:
        db_path.resolve().relative_to(_SANDBOX_ROOT)
        return True
    except ValueError:
        return False


def read_only_contract_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    db_name: str | None,
    trigger_name: str | None,
) -> int:
    """SQLite authorizer callback that permits only read operations.

    Blocks all INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, ATTACH, DETACH,
    and PRAGMA modifications.
    """
    if action in _READ_ONLY_ACTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def validate_read_only_ast(sql: str) -> tuple[bool, str]:
    """Validate that sql is strictly a read-only query using SQLGlot AST inspection.

    Args:
        sql: The SQL statement text to inspect.

    Returns:
        (True, "") if the statement is a safe read-only SELECT query.
        (False, error_reason) if the statement is rejected.
    """
    stripped = sql.strip()
    if not stripped:
        return False, "Contract SQL query statement cannot be empty."

    # Defense-in-depth regex for keywords before parsing
    if _ATTACH_DETACH_RE.match(stripped):
        return False, "ATTACH and DETACH operations are strictly forbidden."

    try:
        statements = [s for s in sqlglot.parse(stripped, read="sqlite") if s is not None]
    except Exception as exc:
        return False, f"SQL syntax parsing failure: {exc}"

    if len(statements) != 1:
        return False, f"Contract must contain exactly 1 SQL statement, got {len(statements)}."

    stmt = statements[0]

    if not isinstance(stmt, _ALLOWED_ROOT_NODES):
        return (
            False,
            f"Statement type '{type(stmt).__name__}' is rejected. "
            "Contracts permit only SELECT and safe WITH...SELECT queries.",
        )

    # Check for mutating sub-expressions
    for disallowed in _DISALLOWED_AST_NODES:
        if stmt.find(disallowed):
            return (
                False,
                f"Disallowed mutating operation '{disallowed.__name__}' detected inside query.",
            )

    return True, ""


# ---------------------------------------------------------------------------
# Execution Engine
# ---------------------------------------------------------------------------


def _execute_contract_query(
    conn: sqlite3.Connection,
    name: str,
    sql: str,
    contract_type: ContractType | str,
) -> ContractResult:
    """Execute a single validated read-only contract query and capture metrics."""
    # 1. AST Read-only check
    is_safe, reject_reason = validate_read_only_ast(sql)
    if not is_safe:
        return ContractResult(
            name=name,
            contract_type=contract_type,
            status=ContractStatus.REJECTED,
            sql_statement=sql,
            execution_time_ms=0.0,
            error_message=reject_reason,
            column_names=(),
        )

    # 2. Execute under authorizer protection
    conn.set_authorizer(read_only_contract_authorizer)
    t0 = time.perf_counter()

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        col_names = tuple(col[0] for col in cursor.description) if cursor.description else ()

        return ContractResult(
            name=name,
            contract_type=contract_type,
            status=ContractStatus.PASS,
            sql_statement=sql,
            execution_time_ms=round(elapsed_ms, 3),
            error_message="",
            column_names=col_names,
            row_count_post=len(rows),
        )
    except sqlite3.DatabaseError as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        err_msg = str(exc)

        # Check if the authorizer intercepted a disallowed operation
        if "not authorized" in err_msg.lower():
            return ContractResult(
                name=name,
                contract_type=contract_type,
                status=ContractStatus.REJECTED,
                sql_statement=sql,
                execution_time_ms=round(elapsed_ms, 3),
                error_message=f"Security authorizer rejected operation: {err_msg}",
                column_names=(),
            )

        # Otherwise it is a standard schema/query execution failure (e.g. column missing)
        return ContractResult(
            name=name,
            contract_type=contract_type,
            status=ContractStatus.FAIL,
            sql_statement=sql,
            execution_time_ms=round(elapsed_ms, 3),
            error_message=err_msg,
            column_names=(),
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return ContractResult(
            name=name,
            contract_type=contract_type,
            status=ContractStatus.FAIL,
            sql_statement=sql,
            execution_time_ms=round(elapsed_ms, 3),
            error_message=str(exc),
            column_names=(),
        )
    finally:
        conn.set_authorizer(None)


def _normalize_contract(
    item: ContractQuery | dict | tuple,
) -> ContractQuery:
    """Normalize various contract representations into a ContractQuery."""
    if isinstance(item, ContractQuery):
        return item
    if isinstance(item, dict):
        return ContractQuery(
            name=item.get("name", "contract"),
            sql=item.get("sql", item.get("sql_statement", "")),
            contract_type=item.get("contract_type", ContractType.OLD_APP),
        )
    if isinstance(item, (tuple, list)):
        c_name = item[0]
        c_sql = item[1]
        c_type = item[2] if len(item) > 2 else ContractType.OLD_APP
        return ContractQuery(name=c_name, sql=c_sql, contract_type=c_type)

    raise TypeError(f"Unsupported contract query type: {type(item).__name__}")


def run_contract(
    sandbox: SandboxContext | sqlite3.Connection | Path | str,
    contract: ContractQuery | dict | tuple,
) -> ContractResult:
    """Execute a single application query contract against the sandbox database.

    Args:
        sandbox: A SandboxContext, an open sandbox Connection, or a verified sandbox Path.
        contract: The contract to execute (ContractQuery, dict, or tuple).

    Returns:
        ContractResult detailing outcome (PASS, FAIL, or REJECTED).
    """
    results = run_contracts(sandbox, [contract])
    return results[0]


def run_contracts(
    sandbox: SandboxContext | sqlite3.Connection | Path | str,
    contracts: Iterable[ContractQuery | dict | tuple],
) -> list[ContractResult]:
    """Execute multiple application query contracts against the sandbox database.

    Execution continues across all contracts even if individual contracts fail
    or are rejected.

    Args:
        sandbox: A SandboxContext, an open Connection, or a verified sandbox file Path.
        contracts: Iterable of contracts to verify.

    Returns:
        List of ContractResult instances in order of execution.

    Raises:
        ValueError: If a filesystem path outside the sandbox root is supplied.
    """
    # 1. Resolve connection and enforce sandbox boundary
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
                f"'{_SANDBOX_ROOT}'. Contracts can only run on sandbox copies."
            )
        conn = sqlite3.connect(str(db_path))
        close_conn = True

    try:
        results: list[ContractResult] = []
        for raw_item in contracts:
            c = _normalize_contract(raw_item)
            res = _execute_contract_query(
                conn=conn,
                name=c.name,
                sql=c.sql,
                contract_type=c.contract_type,
            )
            results.append(res)
        return results
    finally:
        if close_conn and conn is not None:
            conn.close()


def load_contracts_from_dir(directory: Path | str) -> list[ContractQuery]:
    """Load all .sql contract files from a directory.

    Infers contract_type based on filename: files containing 'new_app' are tagged
    as NEW_APP; all others default to OLD_APP.

    Args:
        directory: Path to folder containing contract .sql files.

    Returns:
        Sorted list of ContractQuery objects.
    """
    path = Path(directory)
    if not path.is_dir():
        return []

    contracts: list[ContractQuery] = []
    for file in sorted(path.glob("*.sql")):
        sql_content = file.read_text(encoding="utf-8").strip()
        stem = file.stem
        c_type = ContractType.NEW_APP if "new_app" in stem.lower() else ContractType.OLD_APP
        contracts.append(ContractQuery(name=stem, sql=sql_content, contract_type=c_type))

    return contracts


__all__ = [
    "ContractQuery",
    "ContractType",
    "ContractStatus",
    "ContractResult",
    "validate_read_only_ast",
    "read_only_contract_authorizer",
    "run_contract",
    "run_contracts",
    "load_contracts_from_dir",
]

