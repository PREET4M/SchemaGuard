"""
tests/test_contract_runner.py
-----------------------------
Unit and integration tests for application query contract verification.

Coverage:
- Safe additive migration allows old query contract to PASS.
- Breaking migration (dropping column) causes contract to FAIL with explicit column error.
- Mutation queries (DELETE, UPDATE, INSERT, DROP, ATTACH) are REJECTED by AST/authorizer.
- Zero-row result is treated as PASS.
- Multiple contract batch execution (one failed contract does not halt others).
- Contract types (OLD_APP vs NEW_APP) are correctly recorded.
- Non-sandbox database path is strictly rejected.
- Loading contracts from directory works seamlessly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from schemaguard.core.contract_runner import (
    ContractQuery,
    ContractResult,
    ContractStatus,
    ContractType,
    load_contracts_from_dir,
    run_contract,
    run_contracts,
    validate_read_only_ast,
)
from schemaguard.core.migration_runner import run_migration
from schemaguard.core.sandbox import SandboxContext, create_sandbox


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def source_db(tmp_path: Path) -> Path:
    """Create a sample database with a users table."""
    db_file = tmp_path / "source.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        );
        INSERT INTO users (id, name, email) VALUES
            (1, 'Alice Smith', 'alice@example.test'),
            (2, 'Bob Jones', 'bob@example.test');
        """
    )
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture()
def sandbox(source_db: Path) -> SandboxContext:
    """Create a sandbox copy of source_db, cleaned up after test."""
    ctx = create_sandbox(source_db)
    yield ctx
    ctx.cleanup()


# ===================================================================
# 1. AST Validation Tests
# ===================================================================


class TestAstValidation:
    """Tests for SQLGlot AST read-only validation."""

    def test_select_query_accepted(self) -> None:
        """Standard SELECT query is accepted."""
        ok, reason = validate_read_only_ast("SELECT id, name, email FROM users WHERE id = 1;")
        assert ok is True
        assert reason == ""

    def test_with_select_cte_accepted(self) -> None:
        """Safe WITH...SELECT CTE query is accepted."""
        query = "WITH active AS (SELECT id, name FROM users) SELECT * FROM active;"
        ok, reason = validate_read_only_ast(query)
        assert ok is True
        assert reason == ""

    def test_union_query_accepted(self) -> None:
        """UNION of SELECT queries is accepted."""
        query = "SELECT id FROM users UNION SELECT 999;"
        ok, reason = validate_read_only_ast(query)
        assert ok is True

    def test_empty_query_rejected(self) -> None:
        """Empty query is rejected."""
        ok, reason = validate_read_only_ast("   ")
        assert ok is False
        assert "empty" in reason.lower()

    def test_delete_query_rejected(self) -> None:
        """DELETE statement is rejected."""
        ok, reason = validate_read_only_ast("DELETE FROM users WHERE id = 1;")
        assert ok is False
        assert "Delete" in reason or "rejected" in reason.lower()

    def test_update_query_rejected(self) -> None:
        """UPDATE statement is rejected."""
        ok, reason = validate_read_only_ast("UPDATE users SET name = 'Hacked';")
        assert ok is False
        assert "Update" in reason or "rejected" in reason.lower()

    def test_insert_query_rejected(self) -> None:
        """INSERT statement is rejected."""
        ok, reason = validate_read_only_ast("INSERT INTO users (name, email) VALUES ('X', 'x@test');")
        assert ok is False
        assert "Insert" in reason or "rejected" in reason.lower()

    def test_drop_table_rejected(self) -> None:
        """DROP TABLE statement is rejected."""
        ok, reason = validate_read_only_ast("DROP TABLE users;")
        assert ok is False
        assert "Drop" in reason or "rejected" in reason.lower()

    def test_attach_rejected(self) -> None:
        """ATTACH statement is rejected."""
        ok, reason = validate_read_only_ast("ATTACH DATABASE ':memory:' AS evil;")
        assert ok is False
        assert "forbidden" in reason.lower() or "rejected" in reason.lower()

    def test_multi_statement_injection_rejected(self) -> None:
        """Multi-statement query is rejected."""
        ok, reason = validate_read_only_ast("SELECT 1; DROP TABLE users;")
        assert ok is False
        assert "exactly 1" in reason


# ===================================================================
# 2. Contract Execution: PASS Scenarios
# ===================================================================


class TestContractPass:
    """Tests where contracts execute successfully against sandbox."""

    def test_safe_additive_migration_allows_old_query(self, sandbox: SandboxContext) -> None:
        """After adding a column (phone), existing query for (id, name, email) passes."""
        # Run safe migration
        mig_res = run_migration(sandbox, "ALTER TABLE users ADD COLUMN phone TEXT;")
        assert mig_res.succeeded is True

        # Replay contract
        contract = ContractQuery(
            name="old_app_user_by_id",
            sql="SELECT id, name, email FROM users WHERE id = 1;",
            contract_type=ContractType.OLD_APP,
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.PASS
        assert result.name == "old_app_user_by_id"
        assert result.contract_type == ContractType.OLD_APP
        assert result.column_names == ("id", "name", "email")
        assert result.row_count_post == 1
        assert result.error_message == ""
        assert result.execution_time_ms >= 0.0

    def test_new_app_contract_passes_after_migration(self, sandbox: SandboxContext) -> None:
        """New app contract expecting phone column passes after migration adds it."""
        run_migration(sandbox, "ALTER TABLE users ADD COLUMN phone TEXT;")

        contract = ContractQuery(
            name="new_app_with_phone",
            sql="SELECT id, name, phone FROM users WHERE id = 1;",
            contract_type=ContractType.NEW_APP,
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.PASS
        assert result.contract_type == ContractType.NEW_APP
        assert result.column_names == ("id", "name", "phone")

    def test_zero_rows_query_passes(self, sandbox: SandboxContext) -> None:
        """A valid SELECT that returns zero rows is still considered PASS."""
        contract = ContractQuery(
            name="query_no_rows",
            sql="SELECT id, name FROM users WHERE id = 99999;",
            contract_type=ContractType.OLD_APP,
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.PASS
        assert result.row_count_post == 0
        assert result.column_names == ("id", "name")


# ===================================================================
# 3. Contract Execution: FAIL Scenarios
# ===================================================================


class TestContractFail:
    """Tests where query is valid read-only SQL but fails schema execution."""

    def test_breaking_migration_fails_old_query(self, sandbox: SandboxContext) -> None:
        """Dropping email column causes contract selecting email to FAIL with explicit error."""
        # Execute breaking migration
        mig_res = run_migration(sandbox, "ALTER TABLE users DROP COLUMN email;")
        assert mig_res.succeeded is True

        contract = ContractQuery(
            name="old_app_fetch_email",
            sql="SELECT id, name, email FROM users WHERE id = 1;",
            contract_type=ContractType.OLD_APP,
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.FAIL
        assert result.name == "old_app_fetch_email"
        assert result.column_names == ()
        assert "no such column: email" in result.error_message.lower()

    def test_missing_table_fails(self, sandbox: SandboxContext) -> None:
        """Query referencing a non-existent table fails with explicit error."""
        contract = ContractQuery(
            name="query_missing_table",
            sql="SELECT * FROM non_existent_table;",
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.FAIL
        assert "no such table" in result.error_message.lower()


# ===================================================================
# 4. Contract Execution: REJECTED Scenarios
# ===================================================================


class TestContractRejected:
    """Tests where mutation or disallowed statements are strictly REJECTED."""

    def test_delete_query_rejected(self, sandbox: SandboxContext) -> None:
        """Mutation DELETE query is rejected without modifying database."""
        contract = ContractQuery(
            name="malicious_delete",
            sql="DELETE FROM users;",
        )
        result = run_contract(sandbox, contract)

        assert result.status == ContractStatus.REJECTED
        assert "rejected" in result.error_message.lower() or "delete" in result.error_message.lower()

        # Verify no rows were deleted
        conn = sandbox.connect(readonly=True)
        try:
            count = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
            assert count == 2
        finally:
            conn.close()

    def test_update_query_rejected(self, sandbox: SandboxContext) -> None:
        """Mutation UPDATE query is rejected."""
        contract = ContractQuery(
            name="malicious_update",
            sql="UPDATE users SET name = 'Injected' WHERE id = 1;",
        )
        result = run_contract(sandbox, contract)
        assert result.status == ContractStatus.REJECTED

    def test_pragma_rejected(self, sandbox: SandboxContext) -> None:
        """PRAGMA statement is rejected."""
        contract = ContractQuery(
            name="pragma_attempt",
            sql="PRAGMA writable_schema = ON;",
        )
        result = run_contract(sandbox, contract)
        assert result.status == ContractStatus.REJECTED


# ===================================================================
# 5. Batch Execution & Error Isolation
# ===================================================================


class TestBatchExecution:
    """Tests multiple contract execution ensuring error isolation."""

    def test_batch_continues_after_failure(self, sandbox: SandboxContext) -> None:
        """One failed or rejected contract must not halt subsequent contracts."""
        contracts = [
            ContractQuery(
                name="c1_pass",
                sql="SELECT id, name FROM users WHERE id = 1;",
                contract_type=ContractType.OLD_APP,
            ),
            ContractQuery(
                name="c2_rejected",
                sql="DELETE FROM users;",
                contract_type=ContractType.OLD_APP,
            ),
            ContractQuery(
                name="c3_fail",
                sql="SELECT missing_col FROM users;",
                contract_type=ContractType.OLD_APP,
            ),
            ContractQuery(
                name="c4_pass",
                sql="SELECT email FROM users WHERE id = 2;",
                contract_type=ContractType.OLD_APP,
            ),
        ]

        results = run_contracts(sandbox, contracts)

        assert len(results) == 4
        assert results[0].status == ContractStatus.PASS
        assert results[1].status == ContractStatus.REJECTED
        assert results[2].status == ContractStatus.FAIL
        assert results[3].status == ContractStatus.PASS

    def test_batch_accepts_tuples_and_dicts(self, sandbox: SandboxContext) -> None:
        """run_contracts normalizes tuples and dicts cleanly."""
        items = [
            ("t1", "SELECT id FROM users;"),
            {"name": "t2", "sql": "SELECT name FROM users;"},
        ]
        results = run_contracts(sandbox, items)
        assert len(results) == 2
        assert results[0].status == ContractStatus.PASS
        assert results[1].status == ContractStatus.PASS


# ===================================================================
# 6. Security Boundaries & File Helpers
# ===================================================================


class TestSecurityBoundaries:
    """Tests that security boundaries are strictly enforced."""

    def test_non_sandbox_path_rejected(self, source_db: Path) -> None:
        """Attempting to run contracts directly against original DB raises ValueError."""
        with pytest.raises(ValueError, match="Security policy violation"):
            run_contracts(source_db, [ContractQuery("test", "SELECT 1;")])

    def test_load_contracts_from_demo_dir(self) -> None:
        """Verify loading contracts from data/demo/contracts."""
        demo_dir = Path("data/demo/contracts")
        if demo_dir.is_dir():
            contracts = load_contracts_from_dir(demo_dir)
            assert len(contracts) >= 2
            names = [c.name for c in contracts]
            assert "old_app" in names
            assert "new_app" in names

            # Check that new_app is classified as NEW_APP
            new_contract = next(c for c in contracts if c.name == "new_app")
            assert new_contract.contract_type == ContractType.NEW_APP
