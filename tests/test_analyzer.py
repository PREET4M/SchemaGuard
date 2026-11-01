"""
tests/test_analyzer.py
----------------------
Unit tests for deterministic SQL migration static analysis using SQLGlot.

Coverage:
  - Safe ADD COLUMN migration (no destructive findings)
  - DROP TABLE detection (CRITICAL warning)
  - DROP COLUMN detection (HIGH warning)
  - DELETE and UPDATE without WHERE detection (HIGH warning)
  - Targeted DELETE and UPDATE with valid WHERE (no false positives)
  - Breaking ALTER TABLE operations (MODERATE warning)
  - Syntax error handling for invalid SQL
  - Multi-statement migration parsing and statement indexing
  - Verification of static analysis labels and structured fields
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schemaguard.core.analyzer import (
    RULE_BREAKING_ALTER,
    RULE_DROP_COLUMN,
    RULE_DROP_TABLE,
    RULE_SYNTAX_ERROR,
    RULE_UNBOUNDED_DELETE,
    RULE_UNBOUNDED_UPDATE,
    analyze_migration,
    split_statements,
)
from schemaguard.models import Severity


class TestSafeMigrations:
    """Verifies that safe, non-destructive migrations produce zero destructive warnings."""

    def test_safe_add_column(self) -> None:
        """Safe ALTER TABLE ADD COLUMN should produce no destructive findings."""
        sql = "ALTER TABLE users ADD COLUMN phone TEXT;"
        findings = analyze_migration(sql)
        assert len(findings) == 0
        assert not any(f.is_destructive for f in findings)

    def test_safe_add_column_without_column_keyword(self) -> None:
        """Safe ALTER TABLE ADD <col> <type> without COLUMN keyword is also safe."""
        sql = "ALTER TABLE users ADD phone TEXT;"
        findings = analyze_migration(sql)
        assert len(findings) == 0

    def test_safe_create_table(self) -> None:
        """CREATE TABLE statement is safe and non-destructive."""
        sql = "CREATE TABLE audit_log (id INTEGER PRIMARY KEY, action TEXT);"
        findings = analyze_migration(sql)
        assert len(findings) == 0

    def test_safe_create_index(self) -> None:
        """CREATE INDEX is safe and non-destructive."""
        sql = "CREATE INDEX idx_users_name ON users(name);"
        findings = analyze_migration(sql)
        assert len(findings) == 0

    def test_demo_safe_add_column_file(self) -> None:
        """Verify Phase 2 demo safe migration file (01_safe_add_column.sql)."""
        demo_file = Path("data/demo/migrations/01_safe_add_column.sql")
        if demo_file.exists():
            sql = demo_file.read_text(encoding="utf-8")
            findings = analyze_migration(sql)
            assert len(findings) == 0


class TestDropTableDetection:
    """Verifies detection of DROP TABLE statements."""

    def test_drop_table_basic(self) -> None:
        """Detect standard DROP TABLE with CRITICAL severity."""
        sql = "DROP TABLE order_items;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_DROP_TABLE
        assert f.severity == Severity.CRITICAL
        assert f.is_blocking()
        assert f.is_static
        assert f.is_destructive
        assert f.object_type == "table"
        assert f.object_name == "order_items"
        assert "order_items" in f.title
        assert f.evidence.strip() == "DROP TABLE order_items"
        assert f.statement_index == 0

    def test_drop_table_if_exists(self) -> None:
        """Detect DROP TABLE IF EXISTS."""
        sql = "DROP TABLE IF EXISTS orders;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        assert findings[0].rule_id == RULE_DROP_TABLE
        assert findings[0].object_name == "orders"

    def test_demo_drop_table_file(self) -> None:
        """Verify Phase 2 demo migration file (03_drop_table.sql)."""
        demo_file = Path("data/demo/migrations/03_drop_table.sql")
        if demo_file.exists():
            sql = demo_file.read_text(encoding="utf-8")
            findings = analyze_migration(sql)
            assert len(findings) == 1
            assert findings[0].rule_id == RULE_DROP_TABLE


class TestDropColumnDetection:
    """Verifies detection of DROP COLUMN operations."""

    def test_drop_column_basic(self) -> None:
        """Detect ALTER TABLE ... DROP COLUMN with HIGH severity."""
        sql = "ALTER TABLE users DROP COLUMN email;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_DROP_COLUMN
        assert f.severity == Severity.HIGH
        assert f.is_blocking()
        assert f.is_static
        assert f.is_destructive
        assert f.object_type == "column"
        assert "users" in f.object_name
        assert "email" in f.object_name
        assert "users" in f.title
        assert f.statement_index == 0

    def test_demo_break_old_query_file(self) -> None:
        """Verify Phase 2 demo migration file (02_break_old_query.sql)."""
        demo_file = Path("data/demo/migrations/02_break_old_query.sql")
        if demo_file.exists():
            sql = demo_file.read_text(encoding="utf-8")
            findings = analyze_migration(sql)
            assert len(findings) == 1
            assert findings[0].rule_id == RULE_DROP_COLUMN


class TestUnboundedDmlDetection:
    """Verifies detection of DELETE and UPDATE without WHERE."""

    def test_unbounded_delete(self) -> None:
        """Detect DELETE FROM without WHERE."""
        sql = "DELETE FROM orders;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_UNBOUNDED_DELETE
        assert f.severity == Severity.HIGH
        assert f.is_blocking()
        assert f.is_static
        assert f.is_destructive
        assert f.object_type == "table"
        assert f.object_name == "orders"

    def test_delete_with_trivial_where(self) -> None:
        """Detect DELETE FROM with trivial WHERE 1=1."""
        sql = "DELETE FROM orders WHERE 1 = 1;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        assert findings[0].rule_id == RULE_UNBOUNDED_DELETE

    def test_delete_with_valid_where(self) -> None:
        """Targeted DELETE with legitimate WHERE is not flagged."""
        sql = "DELETE FROM orders WHERE id = 42;"
        findings = analyze_migration(sql)
        assert len(findings) == 0

    def test_unbounded_update(self) -> None:
        """Detect UPDATE without WHERE."""
        sql = "UPDATE users SET status = 'inactive';"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_UNBOUNDED_UPDATE
        assert f.severity == Severity.HIGH
        assert f.is_blocking()
        assert f.is_static
        assert f.is_destructive
        assert f.object_type == "table"
        assert f.object_name == "users"

    def test_update_with_trivial_where(self) -> None:
        """Detect UPDATE with trivial WHERE TRUE."""
        sql = "UPDATE users SET status = 'inactive' WHERE TRUE;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        assert findings[0].rule_id == RULE_UNBOUNDED_UPDATE

    def test_update_with_valid_where(self) -> None:
        """Targeted UPDATE with legitimate WHERE is not flagged."""
        sql = "UPDATE users SET status = 'active' WHERE id = 10;"
        findings = analyze_migration(sql)
        assert len(findings) == 0


class TestBreakingAlterDetection:
    """Verifies detection of breaking ALTER TABLE operations (rename table / rename column)."""

    def test_rename_table(self) -> None:
        """Detect ALTER TABLE ... RENAME TO."""
        sql = "ALTER TABLE users RENAME TO customers;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_BREAKING_ALTER
        assert f.severity == Severity.MODERATE
        assert f.is_static
        assert f.is_destructive
        assert f.object_type == "table"
        assert f.object_name == "users"

    def test_rename_column(self) -> None:
        """Detect ALTER TABLE ... RENAME COLUMN."""
        sql = "ALTER TABLE users RENAME COLUMN name TO full_name;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_BREAKING_ALTER
        assert f.severity == Severity.MODERATE


class TestSyntaxErrorHandling:
    """Verifies graceful handling of invalid SQL syntax."""

    def test_invalid_syntax_captured(self) -> None:
        """Unparseable SQL returns a syntax finding instead of raising an exception."""
        sql = "THIS IS NOT VALID SQL %%^#@;"
        findings = analyze_migration(sql)

        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == RULE_SYNTAX_ERROR
        assert f.severity == Severity.CRITICAL
        assert f.is_blocking()
        assert f.is_static
        assert not f.is_destructive
        assert f.statement_index == 0
        assert "syntax" in f.title.lower() or "syntax" in f.explanation.lower()

    def test_multiple_syntax_errors(self) -> None:
        """Multiple unparseable statements are each captured with their statement_index."""
        sql = "ALTER TABLE; THIS IS NOT VALID SQL %%^#@;"
        findings = analyze_migration(sql)
        assert len(findings) == 2
        assert findings[0].statement_index == 0
        assert findings[1].statement_index == 1

    def test_empty_and_whitespace_sql(self) -> None:
        """Empty or comments-only SQL produces no findings."""
        assert analyze_migration("") == []
        assert analyze_migration("   \n\t  ") == []
        assert analyze_migration("-- just a comment\n/* block comment */") == []


class TestMultiStatementParsing:
    """Verifies multi-statement migration scripts and statement indices."""

    def test_multi_statement_migration(self) -> None:
        """Accurately analyze mixed multi-statement script preserving sequence."""
        script = """
        -- 0: Safe column addition
        ALTER TABLE users ADD COLUMN phone TEXT;

        -- 1: Destructive drop table
        DROP TABLE order_items;

        -- 2: Unbounded delete
        DELETE FROM orders;

        -- 3: Valid targeted update
        UPDATE users SET phone = '555-0100' WHERE id = 1;
        """
        findings = analyze_migration(script)

        # Statements 0 and 3 are safe; statements 1 and 2 produce findings
        assert len(findings) == 2

        f1 = findings[0]
        assert f1.rule_id == RULE_DROP_TABLE
        assert f1.statement_index == 1

        f2 = findings[1]
        assert f2.rule_id == RULE_UNBOUNDED_DELETE
        assert f2.statement_index == 2

    def test_split_statements_handles_embedded_semicolons(self) -> None:
        """Statements with semicolons in string literals are not incorrectly split."""
        script = """
        INSERT INTO logs (message) VALUES ('First; line');
        DROP TABLE temp_logs;
        """
        stmts = split_statements(script)
        assert len(stmts) == 2
        assert "First; line" in stmts[0]
        assert "DROP TABLE" in stmts[1]
