"""
schemaguard/core/analyzer.py
----------------------------
Deterministic static analysis of SQLite migration scripts using SQLGlot.

Detects potentially destructive or contract-breaking DDL/DML statements:
  - SG-ST-000: SQL Syntax Parsing Failure (CRITICAL)
  - SG-ST-001: DROP TABLE (CRITICAL)
  - SG-ST-002: DROP COLUMN (HIGH)
  - SG-ST-003: Unbounded or Bulk DELETE (HIGH)
  - SG-ST-004: Unbounded UPDATE (HIGH)
  - SG-ST-005: Potentially Breaking ALTER TABLE (MODERATE)

Safe operations such as ADD COLUMN or targeted DML with WHERE clauses
do not produce destructive warnings.
"""

from __future__ import annotations

import re
from typing import Final

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.tokens import TokenType

from schemaguard.models import SchemaFinding, Severity, StaticFinding

# ---------------------------------------------------------------------------
# Rule IDs
# ---------------------------------------------------------------------------

RULE_SYNTAX_ERROR: Final[str] = "SG-ST-000"
RULE_DROP_TABLE: Final[str] = "SG-ST-001"
RULE_DROP_COLUMN: Final[str] = "SG-ST-002"
RULE_UNBOUNDED_DELETE: Final[str] = "SG-ST-003"
RULE_UNBOUNDED_UPDATE: Final[str] = "SG-ST-004"
RULE_BREAKING_ALTER: Final[str] = "SG-ST-005"

# Trivial conditions indicating full table operation
_TRIVIAL_WHERE_VALUES: Final[frozenset[str]] = frozenset({"1 = 1", "1=1", "TRUE", "true", "1"})


# ---------------------------------------------------------------------------
# Statement splitting
# ---------------------------------------------------------------------------


def split_statements(sql: str) -> list[str]:
    """Split a multi-statement SQL script into individual statement strings.

    Uses SQLGlot tokenization with SQLite dialect to respect comments and
    semicolons embedded inside quotes or literals. Comments-only blocks
    without actual SQL statements are omitted.

    Args:
        sql: The complete raw SQL migration script.

    Returns:
        List of non-empty, stripped individual SQL statements.
    """
    if not sql or not sql.strip():
        return []

    try:
        tokens = sqlglot.tokenize(sql, read="sqlite")
    except Exception:
        # Fallback to semicolon-based splitting if tokenization fails
        raw_chunks = re.split(r";\s*", sql)
        return [c.strip() for c in raw_chunks if c.strip()]

    # If the script contains only comments or whitespace
    if not tokens:
        return []

    statements: list[str] = []
    current_start = 0

    for token in tokens:
        if token.token_type == TokenType.SEMICOLON:
            chunk = sql[current_start : token.end + 1].strip()
            clean_chunk = chunk.rstrip(";").strip()
            if clean_chunk:
                try:
                    chunk_tokens = sqlglot.tokenize(clean_chunk, read="sqlite")
                except Exception:
                    chunk_tokens = [1]  # Keep so parser can report syntax error

                if chunk_tokens:
                    statements.append(clean_chunk)
            current_start = token.end + 1

    tail = sql[current_start:].rstrip(";").strip()
    if tail:
        try:
            tail_tokens = sqlglot.tokenize(tail, read="sqlite")
        except Exception:
            tail_tokens = [1]
        if tail_tokens:
            statements.append(tail)

    return statements


# ---------------------------------------------------------------------------
# Rule inspection helpers
# ---------------------------------------------------------------------------


def _check_drop_table(
    ast: exp.Expression,
    statement_index: int,
    raw_sql: str,
) -> SchemaFinding | None:
    """Detect DROP TABLE statements (SG-ST-001)."""
    if not isinstance(ast, exp.Drop):
        return None

    kind = getattr(ast, "kind", "")
    if str(kind).upper() != "TABLE":
        return None

    table_node = ast.find(exp.Table)
    table_name = table_node.name if table_node else ""

    return SchemaFinding(
        rule_id=RULE_DROP_TABLE,
        severity=Severity.CRITICAL,
        title=f"DROP TABLE detected: '{table_name}'" if table_name else "DROP TABLE detected",
        explanation=(
            f"Statement permanently drops table '{table_name}' and all contained data."
            if table_name
            else "Statement permanently drops table structure and all data."
        ),
        evidence=raw_sql,
        statement_index=statement_index,
        human_review_action=(
            "Verify whether table removal is intentional and ensure all dependent queries, "
            "foreign keys, and application code are migrated."
        ),
        object_type="table",
        object_name=table_name,
        is_static=True,
        is_destructive=True,
    )


def _check_drop_column(
    ast: exp.Expression,
    statement_index: int,
    raw_sql: str,
) -> list[SchemaFinding]:
    """Detect DROP COLUMN operations inside ALTER TABLE (SG-ST-002)."""
    if not isinstance(ast, exp.Alter):
        return []

    table_name = ast.this.name if hasattr(ast.this, "name") else str(ast.this)
    findings: list[SchemaFinding] = []

    for action in ast.actions:
        if isinstance(action, exp.Drop):
            kind = getattr(action, "kind", "")
            col_node = action.find(exp.Column)
            if str(kind).upper() == "COLUMN" or col_node is not None:
                col_name = col_node.name if col_node else ""
                findings.append(
                    SchemaFinding(
                        rule_id=RULE_DROP_COLUMN,
                        severity=Severity.HIGH,
                        title=(
                            f"DROP COLUMN detected on table '{table_name}'"
                            if table_name
                            else "DROP COLUMN detected"
                        ),
                        explanation=(
                            f"Dropping column '{col_name}' from '{table_name}' permanently "
                            "removes column data and breaks dependent queries."
                            if col_name
                            else f"Dropping column from '{table_name}' permanently deletes data."
                        ),
                        evidence=raw_sql,
                        statement_index=statement_index,
                        human_review_action=(
                            "Ensure no active application queries or contracts rely on this column "
                            "and verify data backup."
                        ),
                        object_type="column",
                        object_name=f"{table_name}.{col_name}" if (table_name and col_name) else table_name,
                        is_static=True,
                        is_destructive=True,
                    )
                )

    return findings


def _is_unbounded_condition(where_node: exp.Where | None) -> bool:
    """Return True if WHERE clause is missing or resolves to a trivial truth condition."""
    if where_node is None:
        return True

    condition_sql = where_node.this.sql(dialect="sqlite").strip()
    return condition_sql in _TRIVIAL_WHERE_VALUES


def _check_unbounded_delete(
    ast: exp.Expression,
    statement_index: int,
    raw_sql: str,
) -> SchemaFinding | None:
    """Detect DELETE FROM without WHERE or with trivial condition (SG-ST-003)."""
    if not isinstance(ast, exp.Delete):
        return None

    where_node = ast.find(exp.Where)
    if not _is_unbounded_condition(where_node):
        return None

    table_node = ast.find(exp.Table)
    table_name = table_node.name if table_node else ""

    return SchemaFinding(
        rule_id=RULE_UNBOUNDED_DELETE,
        severity=Severity.HIGH,
        title=(
            f"Unbounded or bulk DELETE detected on table '{table_name}'"
            if table_name
            else "Unbounded or bulk DELETE detected"
        ),
        explanation=(
            f"DELETE statement on '{table_name}' lacks a restrictive WHERE clause, "
            "which will delete all rows in the table."
            if table_name
            else "DELETE statement lacks a restrictive WHERE clause, purging all rows."
        ),
        evidence=raw_sql,
        statement_index=statement_index,
        human_review_action="Confirm if table truncation is intended or add a targeted WHERE clause.",
        object_type="table",
        object_name=table_name,
        is_static=True,
        is_destructive=True,
    )


def _check_unbounded_update(
    ast: exp.Expression,
    statement_index: int,
    raw_sql: str,
) -> SchemaFinding | None:
    """Detect UPDATE without WHERE or with trivial condition (SG-ST-004)."""
    if not isinstance(ast, exp.Update):
        return None

    where_node = ast.find(exp.Where)
    if not _is_unbounded_condition(where_node):
        return None

    table_node = ast.find(exp.Table)
    table_name = table_node.name if table_node else ""

    return SchemaFinding(
        rule_id=RULE_UNBOUNDED_UPDATE,
        severity=Severity.HIGH,
        title=(
            f"Unbounded UPDATE detected on table '{table_name}'"
            if table_name
            else "Unbounded UPDATE detected"
        ),
        explanation=(
            f"UPDATE statement on '{table_name}' lacks a WHERE clause, which will "
            "overwrite values across all rows."
            if table_name
            else "UPDATE statement lacks a WHERE clause, overwriting all rows."
        ),
        evidence=raw_sql,
        statement_index=statement_index,
        human_review_action="Confirm whether updating every row is intended or add a restricting WHERE clause.",
        object_type="table",
        object_name=table_name,
        is_static=True,
        is_destructive=True,
    )


def _check_breaking_alter(
    ast: exp.Expression,
    statement_index: int,
    raw_sql: str,
) -> list[SchemaFinding]:
    """Detect ALTER TABLE operations that modify structure or rename objects (SG-ST-005).

    Safe operations like ADD COLUMN (ColumnDef) and DROP COLUMN (handled by SG-ST-002)
    are excluded from this general rule.
    """
    if not isinstance(ast, exp.Alter):
        return []

    table_name = ast.this.name if hasattr(ast.this, "name") else str(ast.this)
    findings: list[SchemaFinding] = []

    for action in ast.actions:
        # Safe ADD COLUMN is ColumnDef
        if isinstance(action, exp.ColumnDef):
            continue

        # Handled separately by SG-ST-002
        if isinstance(action, exp.Drop):
            continue

        findings.append(
            SchemaFinding(
                rule_id=RULE_BREAKING_ALTER,
                severity=Severity.MODERATE,
                title=(
                    f"Potentially breaking ALTER TABLE operation on '{table_name}'"
                    if table_name
                    else "ALTER TABLE operation detected"
                ),
                explanation=(
                    f"ALTER TABLE operation on '{table_name}' alters table structure or "
                    "identifiers (e.g. rename), which can invalidate application query contracts."
                    if table_name
                    else "ALTER TABLE operation alters table structure, which can invalidate queries."
                ),
                evidence=raw_sql,
                statement_index=statement_index,
                human_review_action=(
                    "Verify application query contracts and ensure references to renamed or altered "
                    "entities are updated."
                ),
                object_type="table",
                object_name=table_name,
                is_static=True,
                is_destructive=True,
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Public Analysis API
# ---------------------------------------------------------------------------


def analyze_statement(
    ast: exp.Expression,
    statement_index: int = 0,
    raw_sql: str = "",
) -> list[SchemaFinding]:
    """Analyze a single parsed SQL statement AST and return any static findings.

    Args:
        ast: The SQLGlot Expression node.
        statement_index: Positional index in the script.
        raw_sql: The original statement text for evidence formatting.

    Returns:
        List of SchemaFinding objects.
    """
    findings: list[SchemaFinding] = []

    # 1. DROP TABLE
    drop_table_finding = _check_drop_table(ast, statement_index, raw_sql)
    if drop_table_finding:
        findings.append(drop_table_finding)

    # 2. DROP COLUMN
    findings.extend(_check_drop_column(ast, statement_index, raw_sql))

    # 3. Unbounded DELETE
    unbounded_delete_finding = _check_unbounded_delete(ast, statement_index, raw_sql)
    if unbounded_delete_finding:
        findings.append(unbounded_delete_finding)

    # 4. Unbounded UPDATE
    unbounded_update_finding = _check_unbounded_update(ast, statement_index, raw_sql)
    if unbounded_update_finding:
        findings.append(unbounded_update_finding)

    # 5. Potentially breaking ALTER TABLE
    findings.extend(_check_breaking_alter(ast, statement_index, raw_sql))

    return findings


def analyze_migration(sql: str) -> list[SchemaFinding]:
    """Deterministically parse and analyze a migration script using SQLGlot.

    Statements are evaluated with the SQLite dialect. Syntax parsing errors
    are captured as specific CRITICAL findings rather than raising uncaught
    exceptions.

    Args:
        sql: The complete raw SQL migration script.

    Returns:
        List of SchemaFinding objects labeled as static analysis warnings.
    """
    statements = split_statements(sql)
    findings: list[SchemaFinding] = []

    for index, stmt_text in enumerate(statements):
        try:
            ast = sqlglot.parse_one(stmt_text, read="sqlite")
        except SqlglotError as exc:
            findings.append(
                SchemaFinding(
                    rule_id=RULE_SYNTAX_ERROR,
                    severity=Severity.CRITICAL,
                    title="SQL Syntax Parsing Error",
                    explanation=f"SQLGlot could not parse statement using SQLite dialect: {exc}",
                    evidence=stmt_text,
                    statement_index=index,
                    human_review_action="Review and correct the SQL syntax error before applying migration.",
                    object_type="statement",
                    object_name="",
                    is_static=True,
                    is_destructive=False,
                )
            )
            continue

        findings.extend(analyze_statement(ast, statement_index=index, raw_sql=stmt_text))

    return findings


__all__ = [
    "RULE_SYNTAX_ERROR",
    "RULE_DROP_TABLE",
    "RULE_DROP_COLUMN",
    "RULE_UNBOUNDED_DELETE",
    "RULE_UNBOUNDED_UPDATE",
    "RULE_BREAKING_ALTER",
    "SchemaFinding",
    "StaticFinding",
    "split_statements",
    "analyze_statement",
    "analyze_migration",
]
