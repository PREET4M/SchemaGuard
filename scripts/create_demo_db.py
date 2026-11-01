"""
scripts/create_demo_db.py
-------------------------
Deterministically builds the demo SQLite database at `data/demo/ecommerce.db`.

Tables:
  - users(id PRIMARY KEY, name, email UNIQUE, created_at)
  - products(id PRIMARY KEY, name, price, stock)
  - orders(id PRIMARY KEY, user_id FK -> users(id), order_date, status, total)
  - order_items(id PRIMARY KEY, order_id FK -> orders(id), product_id FK -> products(id), quantity, unit_price)

Populates:
  - 10 synthetic users (@example.test domain only)
  - 5 products
  - 12 orders (with associated order items)
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Final

DEFAULT_DB_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "data" / "demo" / "ecommerce.db"
)

SCHEMA_SQL: Final[str] = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    stock INTEGER NOT NULL CHECK(stock >= 0)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'cancelled')),
    total REAL NOT NULL CHECK(total >= 0)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0)
);
"""

USERS_DATA: Final[list[tuple[str, str, str]]] = [
    ("Alice Smith", "alice.smith@example.test", "2026-01-05T09:12:00Z"),
    ("Bob Jones", "bob.jones@example.test", "2026-01-08T14:30:00Z"),
    ("Charlie Brown", "charlie.b@example.test", "2026-01-10T11:45:00Z"),
    ("Diana Prince", "diana.prince@example.test", "2026-01-12T16:20:00Z"),
    ("Evan Wright", "evan.wright@example.test", "2026-01-15T10:05:00Z"),
    ("Fiona Gallagher", "fiona.g@example.test", "2026-01-18T13:15:00Z"),
    ("George Clark", "george.clark@example.test", "2026-01-20T08:50:00Z"),
    ("Hannah Abbott", "hannah.a@example.test", "2026-01-22T17:40:00Z"),
    ("Ian Malcolm", "ian.malcolm@example.test", "2026-01-25T12:00:00Z"),
    ("Julia Roberts", "julia.r@example.test", "2026-01-28T15:25:00Z"),
]

PRODUCTS_DATA: Final[list[tuple[str, float, int]]] = [
    ("Mechanical Keyboard", 120.00, 35),
    ("Wireless Ergonomic Mouse", 45.50, 60),
    ("Ultra-wide 34-inch Monitor", 499.99, 15),
    ("Noise-Cancelling Headphones", 180.00, 25),
    ("USB-C Multiport Hub", 35.00, 80),
]

# (user_id, order_date, status, total, [(product_id, quantity, unit_price), ...])
ORDERS_AND_ITEMS: Final[list[tuple[int, str, str, float, list[tuple[int, int, float]]]]] = [
    (1, "2026-02-01T10:00:00Z", "completed", 165.50, [(1, 1, 120.00), (2, 1, 45.50)]),
    (2, "2026-02-02T11:15:00Z", "completed", 499.99, [(3, 1, 499.99)]),
    (3, "2026-02-03T14:20:00Z", "processing", 180.00, [(4, 1, 180.00)]),
    (4, "2026-02-04T09:40:00Z", "completed", 70.00, [(5, 2, 35.00)]),
    (5, "2026-02-05T16:10:00Z", "pending", 210.50, [(1, 1, 120.00), (2, 2, 45.25)]),
    (6, "2026-02-06T13:00:00Z", "completed", 120.00, [(1, 1, 120.00)]),
    (7, "2026-02-07T12:30:00Z", "cancelled", 35.00, [(5, 1, 35.00)]),
    (8, "2026-02-08T15:45:00Z", "completed", 679.99, [(3, 1, 499.99), (4, 1, 180.00)]),
    (9, "2026-02-09T17:10:00Z", "processing", 91.00, [(2, 2, 45.50)]),
    (10, "2026-02-10T10:25:00Z", "completed", 240.00, [(1, 2, 120.00)]),
    (1, "2026-02-11T11:50:00Z", "pending", 35.00, [(5, 1, 35.00)]),
    (2, "2026-02-12T14:05:00Z", "completed", 180.00, [(4, 1, 180.00)]),
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the SQLite database schema with foreign keys enabled."""
    conn.executescript(SCHEMA_SQL)


def populate_users(conn: sqlite3.Connection) -> None:
    """Insert synthetic users into the users table."""
    conn.executemany(
        "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?);",
        USERS_DATA,
    )


def populate_products(conn: sqlite3.Connection) -> None:
    """Insert product catalog items into the products table."""
    conn.executemany(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?);",
        PRODUCTS_DATA,
    )


def populate_orders(conn: sqlite3.Connection) -> None:
    """Insert orders and related line items."""
    for user_id, order_date, status, total, items in ORDERS_AND_ITEMS:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_id, order_date, status, total) VALUES (?, ?, ?, ?);",
            (user_id, order_date, status, total),
        )
        order_id = cur.lastrowid
        item_rows = [(order_id, pid, qty, unit_price) for pid, qty, unit_price in items]
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
            "VALUES (?, ?, ?, ?);",
            item_rows,
        )


def build_demo_db(target_path: Path = DEFAULT_DB_PATH) -> Path:
    """Build or rebuild the demo SQLite database cleanly and deterministically.

    Args:
        target_path: File system path where `ecommerce.db` will be written.

    Returns:
        The resolved Path of the created database.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path.unlink()

    conn = sqlite3.connect(target_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        create_schema(conn)
        populate_users(conn)
        populate_products(conn)
        populate_orders(conn)
        conn.commit()
    finally:
        conn.close()

    return target_path


if __name__ == "__main__":
    db_file = build_demo_db()
    print(f"Successfully generated demo database at: {db_file}")

