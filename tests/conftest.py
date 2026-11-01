"""
tests/conftest.py
-----------------
Shared pytest fixtures available to every test module in this suite.

Convention:
- Fixtures that create temporary files use ``tmp_path`` (built-in pytest
  fixture) so teardown is automatic.
- No network calls, no real database mutations — all fixtures operate on
  in-memory or temporary copies.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Minimal SQLite database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_db(tmp_path: Path) -> Path:
    """Return the path to a brand-new empty SQLite database file."""
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(db_path)
    conn.close()
    return db_path


@pytest.fixture()
def simple_db(tmp_path: Path) -> Path:
    """Return the path to a SQLite database with one populated table.

    Schema::

        CREATE TABLE users (
            id    INTEGER PRIMARY KEY,
            name  TEXT    NOT NULL,
            email TEXT    UNIQUE NOT NULL
        );

    Seeded with three rows so row-count checks have something to verify.
    """
    db_path = tmp_path / "simple.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id    INTEGER PRIMARY KEY,
            name  TEXT    NOT NULL,
            email TEXT    UNIQUE NOT NULL
        );
        INSERT INTO users (name, email) VALUES
            ('Alice', 'alice@example.com'),
            ('Bob',   'bob@example.com'),
            ('Carol', 'carol@example.com');
        """
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def multi_table_db(tmp_path: Path) -> Path:
    """Return the path to a SQLite database with two related tables.

    Schema::

        users   (id, name, email)
        orders  (id, user_id FK→users.id, amount REAL, status TEXT)

    Seeded with users and orders to exercise foreign-key and join invariants.
    """
    db_path = tmp_path / "multi.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE users (
            id    INTEGER PRIMARY KEY,
            name  TEXT    NOT NULL,
            email TEXT    UNIQUE NOT NULL
        );

        CREATE TABLE orders (
            id      INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount  REAL    NOT NULL CHECK(amount >= 0),
            status  TEXT    NOT NULL DEFAULT 'pending'
        );

        INSERT INTO users (name, email) VALUES
            ('Alice', 'alice@example.com'),
            ('Bob',   'bob@example.com');

        INSERT INTO orders (user_id, amount, status) VALUES
            (1, 99.99,  'completed'),
            (1, 19.50,  'pending'),
            (2, 149.00, 'completed');
        """
    )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Migration SQL snippets
# ---------------------------------------------------------------------------


@pytest.fixture()
def additive_migration_sql() -> str:
    """A safe, additive migration: adds a nullable column to *users*."""
    return "ALTER TABLE users ADD COLUMN created_at TEXT;"


@pytest.fixture()
def destructive_migration_sql() -> str:
    """A destructive migration that drops the *orders* table entirely."""
    return "DROP TABLE orders;"

