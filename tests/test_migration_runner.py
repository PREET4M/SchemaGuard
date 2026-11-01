"""
tests/test_migration_runner.py
-------------------------------
Integration tests for migration execution, security enforcement, and sandbox
isolation.

Coverage:
- Safe additive migrations execute and commit.
- Invalid SQL halts at the failing statement and records index + error.
- ATTACH / DETACH are strictly rejected by the authorizer.
- PRAGMA writable_schema is rejected.
- Foreign key violations are caught and reported.
- Original database is byte-identical before and after rehearsal.
- Non-sandbox paths are rejected outright.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from schemaguard.core.migration_runner import (
    MigrationRunResult,
    StatementOutcome,
    run_migration,
)
from schemaguard.core.sandbox import SandboxContext, create_sandbox
from schemaguard.utils.sql_safety import (
    SqlSafetyError,
    assert_statement_safe,
    install_authorizer,
    remove_authorizer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def source_db(tmp_path: Path) -> Path:
    """Single-table database used as the source for sandbox creation."""
    db = tmp_path / "source.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE users (
            id    INTEGER PRIMARY KEY,
            name  TEXT    NOT NULL,
            email TEXT    UNIQUE NOT NULL
        );
        INSERT INTO users (name, email) VALUES
            ('Alice', 'alice@example.test'),
            ('Bob',   'bob@example.test');
        """
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def fk_source_db(tmp_path: Path) -> Path:
    """Two-table database with an FK relationship for FK violation tests."""
    db = tmp_path / "fk_source.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE users (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE orders (
            id      INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id)
        );
        INSERT INTO users VALUES (1, 'Alice');
        INSERT INTO orders VALUES (1, 1);
        """
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def sandbox(source_db: Path) -> SandboxContext:
    """Live sandbox context; cleaned up after each test."""
    ctx = create_sandbox(source_db)
    yield ctx
    ctx.cleanup()


@pytest.fixture()
def fk_sandbox(fk_source_db: Path) -> SandboxContext:
    """Live sandbox for FK violation tests."""
    ctx = create_sandbox(fk_source_db)
    yield ctx
    ctx.cleanup()


# ===================================================================
# 1. Safe additive migrations
# ===================================================================


class TestSafeAdditive:
    """Safe migrations should succeed, commit, and leave the sandbox consistent."""

    def test_add_column_succeeds(self, sandbox: SandboxContext) -> None:
        """ADD COLUMN migration executes and commits successfully."""
        result = run_migration(sandbox, "ALTER TABLE users ADD COLUMN phone TEXT;")

        assert result.succeeded is True
        assert result.failed_index == -1
        assert result.failed_error == ""
        assert result.post_checks_valid is True
        assert result.rollback_performed is False
        assert len(result.statements) == 1
        assert result.statements[0].succeeded is True
        assert result.statements[0].index == 0
        assert result.total_elapsed_ms >= 0

    def test_add_column_persisted(self, sandbox: SandboxContext) -> None:
        """After successful migration, the new column is visible in the sandbox."""
        run_migration(sandbox, "ALTER TABLE users ADD COLUMN phone TEXT;")

        conn = sandbox.connect(readonly=True)
        try:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(users);").fetchall()]
            assert "phone" in cols
        finally:
            conn.close()

    def test_multi_statement_migration(self, sandbox: SandboxContext) -> None:
        """Multi-statement migration executes all statements in sequence."""
        script = """
        ALTER TABLE users ADD COLUMN phone TEXT;
        ALTER TABLE users ADD COLUMN created_at TEXT;
        INSERT INTO users (name, email, phone) VALUES ('Carol', 'carol@example.test', '555-0100');
        """
        result = run_migration(sandbox, script)

        assert result.succeeded is True
        assert len(result.statements) == 3

        conn = sandbox.connect(readonly=True)
        try:
            row_count = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
            assert row_count == 3
        finally:
            conn.close()

    def test_create_index_migration(self, sandbox: SandboxContext) -> None:
        """CREATE INDEX is safe and should succeed."""
        result = run_migration(sandbox, "CREATE INDEX idx_users_name ON users(name);")
        assert result.succeeded is True

    def test_statement_timing_recorded(self, sandbox: SandboxContext) -> None:
        """Statement elapsed_ms is non-negative and total_elapsed_ms is set."""
        result = run_migration(sandbox, "SELECT 1;")
        assert result.total_elapsed_ms >= 0.0
        assert result.statements[0].elapsed_ms >= 0.0


# ===================================================================
# 2. Failure handling — invalid SQL
# ===================================================================


class TestFailureHandling:
    """Invalid or failing migrations halt at the first error and roll back."""

    def test_invalid_sql_halts(self, sandbox: SandboxContext) -> None:
        """Syntactically invalid SQL halts execution at that statement."""
        result = run_migration(sandbox, "THIS IS NOT VALID SQL;")

        assert result.succeeded is False
        assert result.failed_index == 0
        assert result.failed_error != ""
        assert result.post_checks_valid is False
        assert result.rollback_performed is True

    def test_invalid_sql_records_error_type(self, sandbox: SandboxContext) -> None:
        """The error_type field is populated with the exception class name."""
        result = run_migration(sandbox, "THIS IS NOT VALID SQL;")
        stmt = result.statements[0]
        assert stmt.succeeded is False
        assert stmt.error_type != ""
        assert stmt.error_message != ""

    def test_multi_statement_halts_at_failure_index(self, sandbox: SandboxContext) -> None:
        """For a 3-statement script where statement 1 fails, index is 1."""
        script = """
        ALTER TABLE users ADD COLUMN phone TEXT;
        INSERT INTO nonexistent_table (col) VALUES ('x');
        ALTER TABLE users ADD COLUMN note TEXT;
        """
        result = run_migration(sandbox, script)

        assert result.succeeded is False
        assert result.failed_index == 1
        # Only statements 0 and 1 are recorded (halted at 1)
        assert len(result.statements) == 2
        assert result.statements[0].succeeded is True
        assert result.statements[1].succeeded is False

    def test_failed_migration_rolls_back(self, sandbox: SandboxContext) -> None:
        """Changes from statements before the failure are rolled back."""
        # Statement 0 adds a column but statement 1 fails — whole tx rolls back
        script = """
        ALTER TABLE users ADD COLUMN should_not_persist TEXT;
        INSERT INTO nonexistent_table (col) VALUES ('x');
        """
        run_migration(sandbox, script)

        conn = sandbox.connect(readonly=True)
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users);").fetchall()]
            # Rolled back, so the new column must NOT appear
            assert "should_not_persist" not in cols
        finally:
            conn.close()

    def test_empty_migration_succeeds(self, sandbox: SandboxContext) -> None:
        """An empty migration string is treated as a no-op success."""
        result = run_migration(sandbox, "")
        assert result.succeeded is True
        assert len(result.statements) == 0

    def test_comments_only_migration_succeeds(self, sandbox: SandboxContext) -> None:
        """A script containing only SQL comments is a no-op success."""
        result = run_migration(sandbox, "-- just a comment\n/* another */")
        assert result.succeeded is True


# ===================================================================
# 3. Security — ATTACH / DETACH rejection
# ===================================================================


class TestAttachDetachRejection:
    """ATTACH and DETACH must be blocked at both the static and authorizer layers."""

    def test_attach_rejected_by_safety_check(self) -> None:
        """assert_statement_safe raises SqlSafetyError for ATTACH."""
        with pytest.raises(SqlSafetyError, match="ATTACH"):
            assert_statement_safe('ATTACH DATABASE ":memory:" AS extra;')

    def test_detach_rejected_by_safety_check(self) -> None:
        """assert_statement_safe raises SqlSafetyError for DETACH."""
        with pytest.raises(SqlSafetyError, match="DETACH"):
            assert_statement_safe("DETACH DATABASE extra;")

    def test_attach_in_migration_halts(self, sandbox: SandboxContext) -> None:
        """Running ATTACH inside a migration script is blocked and recorded."""
        result = run_migration(sandbox, 'ATTACH DATABASE ":memory:" AS leak;')

        assert result.succeeded is False
        assert result.failed_index == 0
        assert result.post_checks_valid is False
        assert result.rollback_performed is True
        stmt = result.statements[0]
        assert stmt.error_type == "SqlSafetyError"
        assert "ATTACH" in stmt.error_message

    def test_detach_in_migration_halts(self, sandbox: SandboxContext) -> None:
        """DETACH in a migration is blocked at the pre-execution safety check."""
        result = run_migration(sandbox, "DETACH DATABASE extra;")

        assert result.succeeded is False
        assert result.statements[0].error_type == "SqlSafetyError"
        assert "DETACH" in result.statements[0].error_message

    def test_attach_blocked_by_authorizer_directly(self, source_db: Path) -> None:
        """The authorizer callback denies ATTACH even without the static check."""
        conn = sqlite3.connect(":memory:", isolation_level=None)
        install_authorizer(conn)
        try:
            with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
                conn.execute('ATTACH DATABASE ":memory:" AS extra;')
        finally:
            remove_authorizer(conn)
            conn.close()


# ===================================================================
# 4. Security — PRAGMA writable_schema rejection
# ===================================================================


class TestWritableSchemaRejection:
    """PRAGMA writable_schema must never be executed on a sandbox connection."""

    def test_writable_schema_rejected_by_safety_check(self) -> None:
        """assert_statement_safe raises for PRAGMA writable_schema."""
        with pytest.raises(SqlSafetyError, match="writable_schema"):
            assert_statement_safe("PRAGMA writable_schema = ON;")

    def test_writable_schema_in_migration_halts(self, sandbox: SandboxContext) -> None:
        """PRAGMA writable_schema inside a migration is blocked."""
        result = run_migration(sandbox, "PRAGMA writable_schema = ON;")

        assert result.succeeded is False
        assert result.post_checks_valid is False
        stmt = result.statements[0]
        assert stmt.error_type == "SqlSafetyError"
        assert "writable_schema" in stmt.error_message.lower()

    def test_writable_schema_blocked_by_authorizer(self, source_db: Path) -> None:
        """The authorizer blocks PRAGMA writable_schema even on a direct connection."""
        conn = sqlite3.connect(":memory:", isolation_level=None)
        install_authorizer(conn)
        try:
            with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
                conn.execute("PRAGMA writable_schema = ON;")
        finally:
            remove_authorizer(conn)
            conn.close()


# ===================================================================
# 5. Foreign key violations
# ===================================================================


class TestForeignKeyViolations:
    """FK violations during migration execution must be caught and reported."""

    def test_fk_violation_fails_migration(self, fk_sandbox: SandboxContext) -> None:
        """Inserting a row with an invalid FK reference fails the migration."""
        result = run_migration(
            fk_sandbox,
            "INSERT INTO orders (id, user_id) VALUES (99, 9999);",
        )
        assert result.succeeded is False
        assert result.failed_index == 0
        assert result.post_checks_valid is False
        assert result.rollback_performed is True
        error_msg = result.statements[0].error_message.lower()
        assert "foreign key" in error_msg or "constraint" in error_msg

    def test_fk_violation_rolls_back(self, fk_sandbox: SandboxContext) -> None:
        """After a FK-violating migration, no rows were inserted."""
        run_migration(
            fk_sandbox,
            "INSERT INTO orders (id, user_id) VALUES (99, 9999);",
        )
        conn = fk_sandbox.connect(readonly=True)
        try:
            count = conn.execute("SELECT COUNT(*) FROM orders;").fetchone()[0]
            assert count == 1  # only the pre-existing row
        finally:
            conn.close()


# ===================================================================
# 6. Original database immutability
# ===================================================================


class TestOriginalUnchanged:
    """The source database must be byte-identical after every migration attempt."""

    def test_original_unchanged_after_success(self, source_db: Path) -> None:
        """Successful migration does not touch the source DB."""
        hash_before = _sha256(source_db)
        ctx = create_sandbox(source_db)
        try:
            run_migration(ctx, "ALTER TABLE users ADD COLUMN phone TEXT;")
        finally:
            ctx.cleanup()
        assert _sha256(source_db) == hash_before

    def test_original_unchanged_after_failure(self, source_db: Path) -> None:
        """Failed migration does not touch the source DB."""
        hash_before = _sha256(source_db)
        ctx = create_sandbox(source_db)
        try:
            run_migration(ctx, "DROP TABLE nonexistent_table;")
        finally:
            ctx.cleanup()
        assert _sha256(source_db) == hash_before

    def test_original_unchanged_after_attach_attempt(self, source_db: Path) -> None:
        """Blocked ATTACH attempt does not touch the source DB."""
        hash_before = _sha256(source_db)
        ctx = create_sandbox(source_db)
        try:
            run_migration(ctx, 'ATTACH DATABASE ":memory:" AS leak;')
        finally:
            ctx.cleanup()
        assert _sha256(source_db) == hash_before


# ===================================================================
# 7. Non-sandbox path rejection
# ===================================================================


class TestNonSandboxPathRejection:
    """run_migration must refuse to operate on paths outside the sandbox root."""

    def test_source_path_rejected(self, source_db: Path) -> None:
        """Passing the original source DB path is rejected with ValueError."""
        with pytest.raises(ValueError, match="Security policy violation"):
            run_migration(source_db, "SELECT 1;")

    def test_arbitrary_path_rejected(self, tmp_path: Path) -> None:
        """An arbitrary temp path outside sandbox root is rejected."""
        random_db = tmp_path / "random.db"
        conn = sqlite3.connect(random_db)
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY);")
        conn.commit()
        conn.close()
        with pytest.raises(ValueError, match="Security policy violation"):
            run_migration(random_db, "SELECT 1;")

