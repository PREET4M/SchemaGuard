"""
tests/test_demo_db.py
---------------------
Tests verifying that the demo SQLite database (`data/demo/ecommerce.db`)
is generated deterministically with the expected schema, constraints,
and exact row counts.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts.create_demo_db import (
    DEFAULT_DB_PATH,
    build_demo_db,
)


@pytest.fixture(scope="module")
def demo_db_path() -> Path:
    """Ensure the demo database exists and return its path."""
    return build_demo_db(DEFAULT_DB_PATH)


def test_demo_db_file_exists(demo_db_path: Path) -> None:
    """Assert that the ecommerce.db file is present and non-empty."""
    assert demo_db_path.exists(), f"Expected database at {demo_db_path}"
    assert demo_db_path.stat().st_size > 0, "Database file is empty"


def test_demo_db_table_schemas(demo_db_path: Path) -> None:
    """Verify that all required tables and columns are defined in sqlite_master."""
    expected_tables = {"users", "products", "orders", "order_items"}

    conn = sqlite3.connect(demo_db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # Verify columns on 'users'
        cursor.execute("PRAGMA table_info(users);")
        user_cols = {row[1] for row in cursor.fetchall()}
        assert {"id", "name", "email", "created_at"}.issubset(user_cols)

        # Verify columns on 'products'
        cursor.execute("PRAGMA table_info(products);")
        product_cols = {row[1] for row in cursor.fetchall()}
        assert {"id", "name", "price", "stock"}.issubset(product_cols)

        # Verify columns on 'orders'
        cursor.execute("PRAGMA table_info(orders);")
        order_cols = {row[1] for row in cursor.fetchall()}
        assert {"id", "user_id", "order_date", "status", "total"}.issubset(order_cols)

        # Verify columns on 'order_items'
        cursor.execute("PRAGMA table_info(order_items);")
        item_cols = {row[1] for row in cursor.fetchall()}
        assert {"id", "order_id", "product_id", "quantity", "unit_price"}.issubset(item_cols)
    finally:
        conn.close()


def test_demo_db_row_counts(demo_db_path: Path) -> None:
    """Assert exact expected row counts for all tables."""
    conn = sqlite3.connect(demo_db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        assert user_count == 10, f"Expected 10 users, got {user_count}"

        cursor.execute("SELECT COUNT(*) FROM products;")
        product_count = cursor.fetchone()[0]
        assert product_count == 5, f"Expected 5 products, got {product_count}"

        cursor.execute("SELECT COUNT(*) FROM orders;")
        order_count = cursor.fetchone()[0]
        assert order_count == 12, f"Expected 12 orders, got {order_count}"

        cursor.execute("SELECT COUNT(*) FROM order_items;")
        item_count = cursor.fetchone()[0]
        assert item_count >= 12, f"Expected at least 12 order items, got {item_count}"
    finally:
        conn.close()


def test_users_email_domain(demo_db_path: Path) -> None:
    """Assert that all synthetic users use @example.test domain."""
    conn = sqlite3.connect(demo_db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users;")
        emails = [row[0] for row in cursor.fetchall()]
        for email in emails:
            assert email.endswith("@example.test"), f"Email {email} does not end with @example.test"
    finally:
        conn.close()


def test_demo_db_foreign_key_integrity(demo_db_path: Path) -> None:
    """Assert that foreign key checks find zero violations."""
    conn = sqlite3.connect(demo_db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        assert violations == [], f"Foreign key violations found: {violations}"
    finally:
        conn.close()


def test_recreate_cleanly(tmp_path: Path) -> None:
    """Verify that build_demo_db can recreate the database cleanly at any path."""
    custom_path = tmp_path / "custom_demo.db"
    assert not custom_path.exists()

    build_demo_db(custom_path)
    assert custom_path.exists()

    # Re-run on existing file
    build_demo_db(custom_path)
    assert custom_path.exists()

