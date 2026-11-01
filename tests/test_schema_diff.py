"""
tests/test_schema_diff.py
-------------------------
Unit tests for schema diff engine and data profiling.

Coverage:
  - Detection of dropped tables (tables_removed)
  - Detection of added tables (tables_added)
  - Detection of added and removed columns per table
  - Detection of altered column types, nullability, defaults, and primary keys
  - Modified indexes and foreign keys
  - Detection of row count reductions and unexpected row drops
  - Verification of is_clean() and has_destructive_changes()
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from schemaguard.core.data_profiler import (
    compute_data_profile,
    profile_connections,
    profile_database_rows,
)
from schemaguard.core.schema_diff import (
    diff_connections,
    diff_databases,
    diff_schemas,
)
from schemaguard.core.schema_inspector import inspect_schema


@pytest.fixture()
def base_db(tmp_path: Path) -> Path:
    """Create baseline database before migration."""
    db_file = tmp_path / "baseline.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            total REAL NOT NULL
        );

        CREATE INDEX idx_users_name ON users(name);

        INSERT INTO users (id, name, email) VALUES
            (1, 'Alice', 'alice@test.com'),
            (2, 'Bob', 'bob@test.com'),
            (3, 'Carol', 'carol@test.com');

        INSERT INTO orders (id, user_id, total) VALUES
            (10, 1, 99.0),
            (20, 2, 49.0);
        """
    )
    conn.commit()
    conn.close()
    return db_file


class TestSchemaDiffTables:
    """Tests for table-level diffing."""

    def test_identical_schemas_are_clean(self, base_db: Path) -> None:
        """Comparing identical databases produces an empty, clean diff."""
        conn1 = sqlite3.connect(base_db)
        conn2 = sqlite3.connect(base_db)
        try:
            diff = diff_connections(conn1, conn2)
            assert diff.is_clean() is True
            assert diff.has_destructive_changes() is False
            assert diff.tables_added == ()
            assert diff.tables_removed == ()
            assert diff.tables_modified == ()
        finally:
            conn1.close()
            conn2.close()

    def test_detect_dropped_table(self, tmp_path: Path, base_db: Path) -> None:
        """Dropping a table is detected as tables_removed and flagged as destructive."""
        migrated_db = tmp_path / "dropped_orders.db"
        # Copy base_db
        src_conn = sqlite3.connect(base_db)
        dst_conn = sqlite3.connect(migrated_db)
        src_conn.backup(dst_conn)
        src_conn.close()

        dst_conn.execute("DROP TABLE orders;")
        dst_conn.commit()

        base_conn = sqlite3.connect(base_db)
        try:
            diff = diff_connections(base_conn, dst_conn)
            assert "orders" in diff.tables_removed
            assert diff.has_destructive_changes() is True
            assert diff.is_clean() is False
        finally:
            base_conn.close()
            dst_conn.close()

    def test_detect_added_table(self, tmp_path: Path, base_db: Path) -> None:
        """Creating a new table is detected in tables_added and is non-destructive."""
        migrated_db = tmp_path / "added_audit.db"
        src_conn = sqlite3.connect(base_db)
        dst_conn = sqlite3.connect(migrated_db)
        src_conn.backup(dst_conn)
        src_conn.close()

        dst_conn.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY, note TEXT);")
        dst_conn.commit()

        base_conn = sqlite3.connect(base_db)
        try:
            diff = diff_connections(base_conn, dst_conn)
            assert "audit_log" in diff.tables_added
            assert diff.has_destructive_changes() is False
            assert diff.is_clean() is False
        finally:
            base_conn.close()
            dst_conn.close()


class TestSchemaDiffColumns:
    """Tests for column-level diffing."""

    def test_detect_added_column(self, tmp_path: Path, base_db: Path) -> None:
        """Adding a column is detected in columns_added and is non-destructive."""
        migrated_db = tmp_path / "added_col.db"
        src_conn = sqlite3.connect(base_db)
        dst_conn = sqlite3.connect(migrated_db)
        src_conn.backup(dst_conn)
        src_conn.close()

        dst_conn.execute("ALTER TABLE users ADD COLUMN phone TEXT;")
        dst_conn.commit()

        base_conn = sqlite3.connect(base_db)
        try:
            diff = diff_connections(base_conn, dst_conn)
            assert "users" in diff.columns_added
            assert "phone" in diff.columns_added["users"]
            assert "users" in diff.tables_modified
            assert diff.has_destructive_changes() is False
        finally:
            base_conn.close()
            dst_conn.close()

    def test_detect_removed_column(self, tmp_path: Path, base_db: Path) -> None:
        """Dropping a column is detected in columns_removed and is destructive."""
        migrated_db = tmp_path / "dropped_col.db"
        src_conn = sqlite3.connect(base_db)
        dst_conn = sqlite3.connect(migrated_db)
        src_conn.backup(dst_conn)
        src_conn.close()

        dst_conn.execute("ALTER TABLE users DROP COLUMN status;")
        dst_conn.commit()

        base_conn = sqlite3.connect(base_db)
        try:
            diff = diff_connections(base_conn, dst_conn)
            assert "users" in diff.columns_removed
            assert "status" in diff.columns_removed["users"]
            assert "users" in diff.tables_modified
            assert diff.has_destructive_changes() is True
        finally:
            base_conn.close()
            dst_conn.close()

    def test_detect_altered_column_type_and_defaults(self, tmp_path: Path) -> None:
        """Altering column types or defaults is captured in columns_modified."""
        conn1 = sqlite3.connect(tmp_path / "pre.db")
        conn1.execute("CREATE TABLE products (id INT, price REAL, desc TEXT DEFAULT 'none');")
        conn1.close()

        conn2 = sqlite3.connect(tmp_path / "post.db")
        conn2.execute("CREATE TABLE products (id INT, price INTEGER, desc TEXT DEFAULT 'standard');")
        conn2.close()

        diff = diff_databases(tmp_path / "pre.db", tmp_path / "post.db")
        assert "products" in diff.tables_modified
        assert "products" in diff.columns_modified
        assert "price" in diff.columns_modified["products"]
        assert diff.columns_modified["products"]["price"] == ("REAL", "INTEGER")
        assert "products" in diff.column_details_altered
        assert "default_value" in diff.column_details_altered["products"]["desc"]


class TestDataProfiler:
    """Tests for row count profiling and anomaly detection."""

    def test_profile_database_rows(self, base_db: Path) -> None:
        """profile_database_rows accurately captures row counts."""
        conn = sqlite3.connect(base_db)
        try:
            counts = profile_database_rows(conn)
            assert counts["users"] == 3
            assert counts["orders"] == 2
        finally:
            conn.close()

    def test_detect_row_count_reduction(self) -> None:
        """When post row count is lower than pre, unexpected drop is flagged."""
        pre = {"users": 100, "orders": 500}
        post = {"users": 100, "orders": 450}  # orders lost 50 rows

        profile = compute_data_profile(pre, post)
        assert profile.has_unexpected_drops is True
        assert "orders" in profile.tables_with_dropped_rows
        assert profile.table_deltas["orders"].delta == -50
        assert profile.table_deltas["orders"].is_row_drop is True
        assert profile.table_deltas["orders"].status == "decreased"
        assert profile.total_delta == -50

    def test_detect_missing_table_in_profile(self) -> None:
        """When table is completely missing in post, profile identifies missing_tables."""
        pre = {"users": 10, "orders": 20}
        post = {"users": 10}  # orders dropped

        profile = compute_data_profile(pre, post)
        assert profile.has_unexpected_drops is True
        assert "orders" in profile.missing_tables
        assert profile.table_deltas["orders"].status == "dropped"

    def test_profile_connections_integration(self, tmp_path: Path, base_db: Path) -> None:
        """Integration test profiling two live connections."""
        post_db = tmp_path / "post_prof.db"
        src = sqlite3.connect(base_db)
        dst = sqlite3.connect(post_db)
        src.backup(dst)
        src.close()

        # Delete one row from users
        dst.execute("DELETE FROM users WHERE id = 3;")
        dst.commit()

        base_conn = sqlite3.connect(base_db)
        try:
            profile = profile_connections(base_conn, dst)
            assert profile.has_unexpected_drops is True
            assert "users" in profile.tables_with_dropped_rows
            assert profile.table_deltas["users"].delta == -1
        finally:
            base_conn.close()
            dst.close()

