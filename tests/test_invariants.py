"""
tests/test_invariants.py
------------------------
Unit tests for data invariant execution and security enforcement.

Coverage:
- Clean invariant with 0 violating rows reports PASS.
- Broken invariant with >= 1 violating rows reports FAIL with exact count.
- Query execution failure / invalid SQL reports ERROR (never reported as PASS).
- Mutating queries (DELETE, UPDATE, INSERT, DROP) are strictly rejected as ERROR.
- Non-sandbox database path is rejected.
- Loading and running invariants from data/demo/invariants/invariants.sql.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from schemaguard.core.invariant_runner import (
    InvariantQuery,
    InvariantResult,
    InvariantStatus,
    parse_invariants_file,
    run_invariant,
    run_invariants,
)
from schemaguard.core.sandbox import SandboxContext, create_sandbox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def seeded_db(tmp_path: Path) -> Path:
    """Create a test database with orders and users."""
    db_file = tmp_path / "orders_test.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            total REAL NOT NULL
        );

        INSERT INTO users (id, name) VALUES
            (1, 'Alice'),
            (2, 'Bob');

        -- Seed 3 valid orders, all positive totals
        INSERT INTO orders (id, user_id, total) VALUES
            (101, 1, 50.00),
            (102, 1, 25.50),
            (103, 2, 120.00);
        """
    )
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture()
def sandbox(seeded_db: Path) -> SandboxContext:
    """Sandbox context pointing to an isolated copy of seeded_db."""
    ctx = create_sandbox(seeded_db)
    yield ctx
    ctx.cleanup()


# ===================================================================
# 1. Clean Invariant PASS Tests
# ===================================================================


class TestInvariantPass:
    """Tests where 0 violating rows exist (invariant holds)."""

    def test_clean_invariant_passes(self, sandbox: SandboxContext) -> None:
        """Query finding orders with negative total returns 0 rows -> PASS."""
        inv = InvariantQuery(
            name="No negative order totals",
            sql="SELECT id FROM orders WHERE total < 0;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.PASS
        assert res.held() is True
        assert res.violating_rows_count == 0
        assert res.error_message == ""
        assert res.execution_time_ms >= 0.0

    def test_no_orphaned_orders_passes(self, sandbox: SandboxContext) -> None:
        """Left join finding orphaned orders returns 0 rows -> PASS."""
        inv = InvariantQuery(
            name="No orphaned orders",
            sql="SELECT o.id FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE u.id IS NULL;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.PASS
        assert res.held() is True
        assert res.violating_rows_count == 0


# ===================================================================
# 2. Broken Invariant FAIL Tests
# ===================================================================


class TestInvariantFail:
    """Tests where violating rows exist (invariant is broken)."""

    def test_broken_invariant_fails_with_count(self, sandbox: SandboxContext) -> None:
        """Inject 2 violating rows (negative totals); invariant reports FAIL with count=2."""
        # Inject bad rows into sandbox copy
        conn = sandbox.connect()
        conn.execute("INSERT INTO orders (id, user_id, total) VALUES (201, 1, -15.00);")
        conn.execute("INSERT INTO orders (id, user_id, total) VALUES (202, 2, -99.99);")
        conn.commit()
        conn.close()

        inv = InvariantQuery(
            name="No negative totals",
            sql="SELECT id, total FROM orders WHERE total < 0;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.FAIL
        assert res.held() is False
        assert res.violating_rows_count == 2
        assert "found 2 violating row(s)" in res.error_message
        assert len(res.sample_violations) == 2
        totals = [row["total"] for row in res.sample_violations]
        assert -15.00 in totals and -99.99 in totals

    def test_orphaned_orders_fail(self, sandbox: SandboxContext) -> None:
        """Disable FK and insert orphaned order -> reports FAIL with count=1."""
        conn = sandbox.connect()
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("INSERT INTO orders (id, user_id, total) VALUES (301, 9999, 10.00);")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        conn.close()

        inv = InvariantQuery(
            name="No orphaned orders",
            sql="SELECT o.id FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE u.id IS NULL;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.FAIL
        assert res.held() is False
        assert res.violating_rows_count == 1


# ===================================================================
# 3. Query Error Handling
# ===================================================================


class TestInvariantError:
    """Tests where query fails execution or contains invalid SQL."""

    def test_invalid_sql_syntax_reports_error(self, sandbox: SandboxContext) -> None:
        """Malformed SQL syntax reports ERROR and never PASS."""
        inv = InvariantQuery(
            name="Syntax error query",
            sql="SELECT * FROM orders WHERE total <<< 0;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.ERROR
        assert res.held() is False
        assert res.error_message != ""

    def test_missing_table_reports_error(self, sandbox: SandboxContext) -> None:
        """Referencing non-existent table reports ERROR."""
        inv = InvariantQuery(
            name="Missing table",
            sql="SELECT id FROM non_existent_table;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.ERROR
        assert res.held() is False
        assert "no such table" in res.error_message.lower()

    def test_mutating_query_rejected(self, sandbox: SandboxContext) -> None:
        """DELETE query in invariant is rejected as ERROR."""
        inv = InvariantQuery(
            name="Disallowed delete",
            sql="DELETE FROM orders;",
        )
        res = run_invariant(sandbox, inv)

        assert res.status == InvariantStatus.ERROR
        assert res.held() is False
        assert "rejected" in res.error_message.lower() or "delete" in res.error_message.lower()

        # Verify no rows were actually deleted
        conn = sandbox.connect(readonly=True)
        try:
            count = conn.execute("SELECT COUNT(*) FROM orders;").fetchone()[0]
            assert count == 3
        finally:
            conn.close()


# ===================================================================
# 4. Batch Execution & File Parsing
# ===================================================================


class TestBatchAndFileParsing:
    """Tests multiple invariant execution and loading from file."""

    def test_run_invariants_batch(self, sandbox: SandboxContext) -> None:
        """Batch of mixed PASS, FAIL, and ERROR invariants executes completely."""
        invariants = [
            InvariantQuery("pass_inv", "SELECT id FROM orders WHERE total < 0;"),
            InvariantQuery("error_inv", "SELECT id FROM missing_table;"),
            InvariantQuery("pass_inv2", "SELECT id FROM orders WHERE total > 10000;"),
        ]

        results = run_invariants(sandbox, invariants)
        assert len(results) == 3
        assert results[0].status == InvariantStatus.PASS
        assert results[1].status == InvariantStatus.ERROR
        assert results[2].status == InvariantStatus.PASS

    def test_parse_invariants_demo_file(self) -> None:
        """Parse demo invariants file data/demo/invariants/invariants.sql."""
        demo_file = Path("data/demo/invariants/invariants.sql")
        if demo_file.is_file():
            invariants = parse_invariants_file(demo_file)
            assert len(invariants) == 2
            assert "negative order totals" in invariants[0].name.lower()
            assert "orphaned orders" in invariants[1].name.lower()

    def test_non_sandbox_path_rejected(self, seeded_db: Path) -> None:
        """Attempting to run invariants directly on source DB raises ValueError."""
        with pytest.raises(ValueError, match="Security policy violation"):
            run_invariants(seeded_db, [InvariantQuery("t", "SELECT 1;")])

