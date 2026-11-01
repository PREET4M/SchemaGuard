"""
tests/test_sandbox.py
---------------------
Tests for file validation, schema inspection, and sandbox lifecycle.

Coverage goals:
- Original database remains **strictly unchanged** (file-hash verification).
- Sandbox copy matches the source schema and row counts.
- Cleanup removes temporary directories.
- Invalid, oversized, and corrupted files are rejected.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from schemaguard.core.sandbox import SandboxContext, create_sandbox
from schemaguard.core.schema_inspector import (
    get_columns,
    get_foreign_keys,
    get_indexes,
    get_row_count,
    get_tables,
    inspect_schema,
)
from schemaguard.utils.file_validation import FileValidationError, validate_sqlite_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ===================================================================
# 1. File validation
# ===================================================================


class TestFileValidation:
    """Tests for :mod:`schemaguard.utils.file_validation`."""

    def test_valid_sqlite_file(self, simple_db: Path) -> None:
        """A genuine SQLite DB passes all checks and returns resolved path."""
        result = validate_sqlite_file(simple_db)
        assert result == simple_db.resolve()

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Raise FileValidationError for a path that does not exist."""
        fake = tmp_path / "nope.db"
        with pytest.raises(FileValidationError, match="does not exist"):
            validate_sqlite_file(fake)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Raise FileValidationError for a zero-byte file."""
        empty = tmp_path / "empty.db"
        empty.touch()
        with pytest.raises(FileValidationError, match="empty"):
            validate_sqlite_file(empty)

    def test_oversized_file(self, simple_db: Path) -> None:
        """Raise FileValidationError when file exceeds max_size_bytes."""
        with pytest.raises(FileValidationError, match="too large"):
            validate_sqlite_file(simple_db, max_size_bytes=1)

    def test_corrupted_file(self, tmp_path: Path) -> None:
        """Raise FileValidationError for a file with garbage bytes."""
        bad = tmp_path / "bad.db"
        bad.write_bytes(b"This is definitely not a SQLite database file.")
        with pytest.raises(FileValidationError, match="valid SQLite header"):
            validate_sqlite_file(bad)

    def test_bad_header_good_extension(self, tmp_path: Path) -> None:
        """A .db file with wrong header bytes is rejected."""
        fake = tmp_path / "looks_legit.db"
        fake.write_bytes(b"\x00" * 100)
        with pytest.raises(FileValidationError, match="valid SQLite header"):
            validate_sqlite_file(fake)

    def test_directory_rejected(self, tmp_path: Path) -> None:
        """A directory path is not a regular file."""
        with pytest.raises(FileValidationError, match="not a regular file"):
            validate_sqlite_file(tmp_path)


# ===================================================================
# 2. Schema inspector
# ===================================================================


class TestSchemaInspector:
    """Tests for :mod:`schemaguard.core.schema_inspector`."""

    def test_get_tables(self, simple_db: Path) -> None:
        """Returns the expected list of user tables."""
        conn = sqlite3.connect(simple_db)
        try:
            tables = get_tables(conn)
            assert tables == ["users"]
        finally:
            conn.close()

    def test_get_tables_multi(self, multi_table_db: Path) -> None:
        """Returns both tables sorted alphabetically."""
        conn = sqlite3.connect(multi_table_db)
        try:
            tables = get_tables(conn)
            assert tables == ["orders", "users"]
        finally:
            conn.close()

    def test_get_columns(self, simple_db: Path) -> None:
        """Column metadata matches the CREATE TABLE definition."""
        conn = sqlite3.connect(simple_db)
        try:
            cols = get_columns(conn, "users")
            col_names = [c.name for c in cols]
            assert col_names == ["id", "name", "email"]
            # id is the primary key
            assert cols[0].pk == 1
            # name is NOT NULL
            assert cols[1].notnull is True
        finally:
            conn.close()

    def test_get_indexes(self, simple_db: Path) -> None:
        """Users table has at least the UNIQUE index on email."""
        conn = sqlite3.connect(simple_db)
        try:
            indexes = get_indexes(conn, "users")
            unique_indexes = [idx for idx in indexes if idx.unique]
            assert len(unique_indexes) >= 1
            # One of the unique indexes should cover email
            email_covered = any("email" in idx.columns for idx in unique_indexes)
            assert email_covered
        finally:
            conn.close()

    def test_get_foreign_keys(self, multi_table_db: Path) -> None:
        """Orders table has a FK referencing users."""
        conn = sqlite3.connect(multi_table_db)
        try:
            fks = get_foreign_keys(conn, "orders")
            assert len(fks) >= 1
            fk = fks[0]
            assert fk.table == "users"
            assert fk.from_col == "user_id"
            assert fk.to_col == "id"
        finally:
            conn.close()

    def test_get_row_count(self, simple_db: Path) -> None:
        """Row count matches the seeded data."""
        conn = sqlite3.connect(simple_db)
        try:
            assert get_row_count(conn, "users") == 3
        finally:
            conn.close()

    def test_inspect_schema_snapshot(self, multi_table_db: Path) -> None:
        """inspect_schema returns a snapshot covering all tables."""
        conn = sqlite3.connect(multi_table_db)
        try:
            schema = inspect_schema(conn)
            assert set(schema.keys()) == {"users", "orders"}
            assert schema["users"].row_count == 2
            assert schema["orders"].row_count == 3
            assert len(schema["orders"].foreign_keys) >= 1
        finally:
            conn.close()


# ===================================================================
# 3. Sandbox lifecycle
# ===================================================================


class TestSandbox:
    """Tests for :mod:`schemaguard.core.sandbox`."""

    def test_original_unchanged_after_sandbox(self, simple_db: Path) -> None:
        """The source database is byte-identical before and after sandbox creation."""
        hash_before = _file_sha256(simple_db)

        ctx = create_sandbox(simple_db)
        try:
            # Mutate the sandbox copy
            conn = ctx.connect()
            conn.execute("ALTER TABLE users ADD COLUMN phone TEXT;")
            conn.execute("INSERT INTO users (name, email) VALUES ('Zoe', 'zoe@test.com');")
            conn.commit()
            conn.close()
        finally:
            ctx.cleanup()

        hash_after = _file_sha256(simple_db)
        assert hash_before == hash_after, "Source database was modified!"

    def test_sandbox_schema_matches_source(self, multi_table_db: Path) -> None:
        """The sandbox copy has the same tables, columns, and row counts."""
        ctx = create_sandbox(multi_table_db)
        try:
            # Inspect source
            src_conn = sqlite3.connect(multi_table_db)
            src_schema = inspect_schema(src_conn)
            src_conn.close()

            # Inspect sandbox
            sb_conn = ctx.connect(readonly=True)
            sb_schema = inspect_schema(sb_conn)
            sb_conn.close()

            assert set(src_schema.keys()) == set(sb_schema.keys())
            for table_name in src_schema:
                src_t = src_schema[table_name]
                sb_t = sb_schema[table_name]
                assert src_t.row_count == sb_t.row_count
                assert len(src_t.columns) == len(sb_t.columns)
                for src_c, sb_c in zip(src_t.columns, sb_t.columns):
                    assert src_c.name == sb_c.name
                    assert src_c.col_type == sb_c.col_type
        finally:
            ctx.cleanup()

    def test_cleanup_removes_directory(self, simple_db: Path) -> None:
        """After cleanup(), the sandbox directory no longer exists."""
        ctx = create_sandbox(simple_db)
        sandbox_dir = ctx.sandbox_dir

        assert sandbox_dir.exists()
        assert ctx.is_alive

        ctx.cleanup()

        assert not sandbox_dir.exists()
        assert not ctx.is_alive

    def test_cleanup_idempotent(self, simple_db: Path) -> None:
        """Calling cleanup() multiple times does not raise."""
        ctx = create_sandbox(simple_db)
        ctx.cleanup()
        ctx.cleanup()  # second call is a no-op
        assert not ctx.is_alive

    def test_rejects_nonexistent_file(self, tmp_path: Path) -> None:
        """create_sandbox raises for a path that does not exist."""
        fake = tmp_path / "ghost.db"
        with pytest.raises(FileValidationError, match="does not exist"):
            create_sandbox(fake)

    def test_rejects_oversized_file(self, simple_db: Path) -> None:
        """create_sandbox raises when max_size_bytes is exceeded."""
        with pytest.raises(FileValidationError, match="too large"):
            create_sandbox(simple_db, max_size_bytes=1)

    def test_rejects_corrupted_file(self, tmp_path: Path) -> None:
        """create_sandbox raises for a file with invalid content."""
        bad = tmp_path / "corrupt.db"
        bad.write_bytes(b"not a database at all, just random bytes here")
        with pytest.raises(FileValidationError, match="valid SQLite header"):
            create_sandbox(bad)

    def test_sandbox_writable_while_source_untouched(
        self, simple_db: Path
    ) -> None:
        """Writes to the sandbox succeed and do not touch the source."""
        hash_before = _file_sha256(simple_db)

        ctx = create_sandbox(simple_db)
        try:
            conn = ctx.connect()
            conn.execute("CREATE TABLE new_table (id INTEGER PRIMARY KEY, val TEXT);")
            conn.execute("INSERT INTO new_table (val) VALUES ('hello');")
            conn.commit()

            # Verify the new table exists in the sandbox
            tables = get_tables(conn)
            assert "new_table" in tables
            assert get_row_count(conn, "new_table") == 1
            conn.close()

            # Verify the new table does NOT exist in the source
            src_conn = sqlite3.connect(simple_db)
            src_tables = get_tables(src_conn)
            src_conn.close()
            assert "new_table" not in src_tables
        finally:
            ctx.cleanup()

        assert _file_sha256(simple_db) == hash_before

    def test_no_leftover_sandbox_on_invalid_input(self, tmp_path: Path) -> None:
        """No sandbox directory is left behind when validation fails."""
        bad = tmp_path / "invalid.db"
        bad.write_bytes(b"garbage content filling up bytes")

        from schemaguard.config import SANDBOX_DIR

        sandbox_root = Path(SANDBOX_DIR)
        dirs_before = set(sandbox_root.iterdir()) if sandbox_root.exists() else set()

        with pytest.raises(FileValidationError):
            create_sandbox(bad)

        dirs_after = set(sandbox_root.iterdir()) if sandbox_root.exists() else set()
        new_dirs = dirs_after - dirs_before
        assert len(new_dirs) == 0, f"Leftover sandbox dirs: {new_dirs}"

