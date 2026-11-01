"""
tests/test_end_to_end.py
------------------------
End-to-end integration tests verifying the complete SchemaGuard pipeline:

Scenarios:
  - Scenario A (Safe Migration):
      ALTER TABLE users ADD COLUMN phone TEXT;
      -> Execution passes, old query passes, invariants pass, severity LOW ("No configured checks failed").
  - Scenario B (Breaking Migration):
      ALTER TABLE users DROP COLUMN email;
      -> Execution succeeds, old query contract (selecting email) FAILS, severity CRITICAL.
  - Scenario C (Invalid SQL):
      ALTER TABLE users ADD COLUMN;
      -> Execution FAILS, error recorded, post checks marked skipped.
  - Scenario D (Invariant Violation):
      Controlled migration that inserts an invalid negative total
      -> Invariant returns FAIL with violation count.
  - Scenario E (Immutability):
      Verify source DB SHA-256 hash remains 100% identical before and after rehearsal,
      and no sandbox directories leak on disk.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from schemaguard.config import SANDBOX_DIR
from schemaguard.core.contract_runner import ContractStatus, ContractType
from schemaguard.core.invariant_runner import InvariantStatus
from schemaguard.core.orchestrator import rehearse_migration
from schemaguard.models import Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    """Calculate the SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_db(tmp_path: Path) -> Path:
    """Create a pristine sample database for end-to-end rehearsal tests."""
    db_path = tmp_path / "e2e_source.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            total REAL NOT NULL
        );

        INSERT INTO users (name, email, created_at) VALUES
            ('Alice Smith', 'alice@example.test', '2026-01-01T10:00:00Z'),
            ('Bob Jones',   'bob@example.test',   '2026-01-02T11:00:00Z'),
            ('Carol White', 'carol@example.test', '2026-01-03T12:00:00Z');

        INSERT INTO orders (user_id, total) VALUES
            (1, 150.00),
            (1, 45.50),
            (2, 299.99);
        """
    )
    conn.commit()
    conn.close()
    return db_path


# ===================================================================
# End-to-End Scenarios
# ===================================================================


class TestEndToEndScenarios:
    """Integration test suite covering all end-to-end rehearsal scenarios."""

    def test_scenario_a_safe_migration(self, test_db: Path) -> None:
        """Scenario A: Safe additive migration passes all checks with LOW risk."""
        migration_sql = "ALTER TABLE users ADD COLUMN phone TEXT;"
        old_contracts = ["SELECT id, name, email FROM users WHERE id = 1;"]
        new_contracts = ["SELECT id, name, phone FROM users WHERE id = 1;"]
        invariants = ["SELECT id FROM orders WHERE total < 0;"]

        report = rehearse_migration(
            source_db_path=test_db,
            migration_sql=migration_sql,
            old_app_contracts=old_contracts,
            new_app_contracts=new_contracts,
            invariants=invariants,
        )

        # Verification
        assert report.migration_result.migration_applied is True
        assert report.post_checks_run is True
        assert report.severity == Severity.LOW
        assert report.label == "No configured checks failed"
        assert report.risk_score == 0
        assert report.can_auto_approve is True
        assert report.succeeded is True

        # Contracts check
        contracts = report.migration_result.contract_results
        assert len(contracts) == 2
        assert all(c.status == ContractStatus.PASS for c in contracts)

        # Invariants check
        invariants_res = report.migration_result.invariant_results
        assert len(invariants_res) == 1
        assert invariants_res[0].status == InvariantStatus.PASS
        assert invariants_res[0].violating_rows_count == 0

        # Schema Diff check
        diff = report.migration_result.schema_diff
        assert "users" in diff.columns_added
        assert "phone" in diff.columns_added["users"]
        assert diff.has_destructive_changes() is False

    def test_scenario_b_breaking_migration(self, test_db: Path) -> None:
        """Scenario B: Dropping email column breaks old query contract -> CRITICAL."""
        migration_sql = "ALTER TABLE users DROP COLUMN email;"
        old_contracts = ["SELECT id, name, email FROM users WHERE id = 1;"]

        report = rehearse_migration(
            source_db_path=test_db,
            migration_sql=migration_sql,
            old_app_contracts=old_contracts,
        )

        assert report.migration_result.migration_applied is True
        assert report.post_checks_run is True
        assert report.severity == Severity.CRITICAL
        assert report.can_auto_approve is False
        assert report.succeeded is False

        # Verify old contract failed specifically on missing column
        failed_contracts = report.migration_result.failed_contracts()
        assert len(failed_contracts) == 1
        assert "no such column: email" in failed_contracts[0].error_message.lower()

        # Schema Diff reflects removed column
        diff = report.migration_result.schema_diff
        assert "users" in diff.columns_removed
        assert "email" in diff.columns_removed["users"]
        assert diff.has_destructive_changes() is True

    def test_scenario_c_invalid_sql(self, test_db: Path) -> None:
        """Scenario C: Invalid SQL syntax halts execution and marks post-checks skipped."""
        migration_sql = "ALTER TABLE users ADD COLUMN;"  # Incomplete syntax
        old_contracts = ["SELECT id, name FROM users;"]

        report = rehearse_migration(
            source_db_path=test_db,
            migration_sql=migration_sql,
            old_app_contracts=old_contracts,
        )

        assert report.migration_result.migration_applied is False
        assert report.post_checks_run is False
        assert report.migration_result.migration_error != ""
        assert report.severity == Severity.CRITICAL
        assert report.risk_score == 100
        assert report.succeeded is False

        # Post checks were skipped
        assert len(report.migration_result.contract_results) == 0
        assert len(report.migration_result.invariant_results) == 0

    def test_scenario_d_invariant_violation(self, test_db: Path) -> None:
        """Scenario D: Migration inserting bad data triggers invariant FAIL."""
        migration_sql = "INSERT INTO orders (user_id, total) VALUES (1, -49.99);"
        invariants = ["SELECT id, total FROM orders WHERE total < 0;"]

        report = rehearse_migration(
            source_db_path=test_db,
            migration_sql=migration_sql,
            invariants=invariants,
        )

        assert report.migration_result.migration_applied is True
        assert report.post_checks_run is True
        assert report.severity == Severity.HIGH
        assert report.can_auto_approve is False

        inv_res = report.migration_result.invariant_results[0]
        assert inv_res.status == InvariantStatus.FAIL
        assert inv_res.violating_rows_count == 1
        assert len(inv_res.sample_violations) == 1
        assert inv_res.sample_violations[0]["total"] == -49.99

    def test_scenario_e_source_immutability(self, test_db: Path) -> None:
        """Scenario E: Verify original database remains 100% byte-identical across rehearsals."""
        original_hash = _sha256(test_db)

        # Run multiple contrasting rehearsals
        rehearse_migration(
            test_db,
            "ALTER TABLE users ADD COLUMN phone TEXT;",
        )
        assert _sha256(test_db) == original_hash

        rehearse_migration(
            test_db,
            "DROP TABLE orders;",
        )
        assert _sha256(test_db) == original_hash

        rehearse_migration(
            test_db,
            "SYNTAX ERROR INVALID SQL;",
        )
        assert _sha256(test_db) == original_hash

        rehearse_migration(
            test_db,
            "DELETE FROM users;",
        )
        assert _sha256(test_db) == original_hash

    def test_no_sandbox_leak(self, test_db: Path) -> None:
        """Ensure all temporary sandbox directories are cleaned up after rehearsal."""
        sandbox_root = Path(SANDBOX_DIR)
        before_dirs = set(sandbox_root.iterdir()) if sandbox_root.exists() else set()

        rehearse_migration(
            test_db,
            "ALTER TABLE users ADD COLUMN notes TEXT;",
            old_app_contracts=["SELECT * FROM users;"],
        )

        after_dirs = set(sandbox_root.iterdir()) if sandbox_root.exists() else set()
        leaked = after_dirs - before_dirs
        assert len(leaked) == 0, f"Leaked sandbox directories: {leaked}"

    def test_report_export_helpers(self, test_db: Path, tmp_path: Path) -> None:
        """Verify report serialization and file export helpers."""
        report = rehearse_migration(
            source_db_path=test_db,
            migration_sql="ALTER TABLE users ADD COLUMN avatar_url TEXT;",
        )

        # In-memory export
        json_str = report.to_json()
        assert "avatar_url" in json_str
        assert "No configured checks failed" in json_str

        md_str = report.to_markdown()
        assert "# 🛡️ SchemaGuard — Migration Rehearsal Report" in md_str
        assert "avatar_url" in md_str

        # File export
        json_file = tmp_path / "out" / "rehearsal.json"
        md_file = tmp_path / "out" / "rehearsal.md"

        ret_json = report.export_json(json_file)
        ret_md = report.export_markdown(md_file)

        assert ret_json.is_file()
        assert ret_md.is_file()
        assert ret_json.stat().st_size > 0
        assert ret_md.stat().st_size > 0

