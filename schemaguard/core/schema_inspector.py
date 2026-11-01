"""
schemaguard/core/schema_inspector.py
------------------------------------
Read-only introspection of an open SQLite connection.

Returns structured dictionaries (and typed dataclasses for columns) so that
callers can diff two snapshots purely in Python without re-querying the DB.

Public API
~~~~~~~~~~
- :func:`inspect_schema` — full schema snapshot in one call.
- :func:`get_tables` — list user table names.
- :func:`get_columns` — column metadata for a single table.
- :func:`get_indexes` — index metadata for a single table.
- :func:`get_foreign_keys` — FK constraints for a single table.
- :func:`get_row_count` — row count for a single table.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnInfo:
    """Metadata for a single column, mirroring ``PRAGMA table_info`` output.

    Attributes:
        cid:          Column index (0-based).
        name:         Column name.
        col_type:     Declared type string (may be empty for typeless cols).
        notnull:      ``True`` if the column has a NOT NULL constraint.
        default_value: Default value expression, or ``None``.
        pk:           Primary-key index (1-based), or ``0`` if not a PK.
    """

    cid: int
    name: str
    col_type: str
    notnull: bool
    default_value: Any
    pk: int


@dataclass(frozen=True)
class IndexInfo:
    """Metadata for a single index on a table.

    Attributes:
        name:      Index name (``None`` for auto-created implicit indexes).
        unique:    ``True`` if this is a UNIQUE index.
        origin:    How the index was created: ``'c'`` (CREATE INDEX),
                   ``'u'`` (UNIQUE constraint), or ``'pk'`` (PRIMARY KEY).
        columns:   Ordered tuple of column names covered by the index.
    """

    name: str | None
    unique: bool
    origin: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class ForeignKeyInfo:
    """Metadata for a single foreign-key constraint.

    Attributes:
        id:           FK constraint id (groups multi-column FKs).
        seq:          Column sequence within the constraint (0-based).
        table:        Referenced (parent) table name.
        from_col:     Column in the child table.
        to_col:       Column in the parent table.
        on_update:    ON UPDATE action string.
        on_delete:    ON DELETE action string.
    """

    id: int
    seq: int
    table: str
    from_col: str
    to_col: str
    on_update: str
    on_delete: str


@dataclass(frozen=True)
class TableSchema:
    """Complete schema snapshot for a single table.

    Attributes:
        name:          Table name.
        columns:       Ordered tuple of :class:`ColumnInfo`.
        indexes:       Tuple of :class:`IndexInfo`.
        foreign_keys:  Tuple of :class:`ForeignKeyInfo`.
        row_count:     Number of rows at the time of inspection.
    """

    name: str
    columns: tuple[ColumnInfo, ...] = field(default_factory=tuple)
    indexes: tuple[IndexInfo, ...] = field(default_factory=tuple)
    foreign_keys: tuple[ForeignKeyInfo, ...] = field(default_factory=tuple)
    row_count: int = 0


# ---------------------------------------------------------------------------
# Low-level query helpers
# ---------------------------------------------------------------------------


def get_tables(conn: sqlite3.Connection) -> list[str]:
    """Return sorted names of all user tables (excluding internal SQLite tables).

    Args:
        conn: An open SQLite connection.
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name;"
    )
    return [row[0] for row in cursor.fetchall()]


def get_columns(conn: sqlite3.Connection, table: str) -> tuple[ColumnInfo, ...]:
    """Return column metadata for *table*, ordered by column index.

    Args:
        conn:  An open SQLite connection.
        table: Name of the table to inspect.
    """
    cursor = conn.execute(f"PRAGMA table_info('{table}');")
    return tuple(
        ColumnInfo(
            cid=row[0],
            name=row[1],
            col_type=row[2] or "",
            notnull=bool(row[3]),
            default_value=row[4],
            pk=row[5],
        )
        for row in cursor.fetchall()
    )


def get_indexes(conn: sqlite3.Connection, table: str) -> tuple[IndexInfo, ...]:
    """Return index metadata for *table*.

    Args:
        conn:  An open SQLite connection.
        table: Name of the table to inspect.
    """
    cursor = conn.execute(f"PRAGMA index_list('{table}');")
    indexes: list[IndexInfo] = []
    for row in cursor.fetchall():
        idx_name: str = row[1]
        unique: bool = bool(row[2])
        origin: str = row[3]

        col_cursor = conn.execute(f"PRAGMA index_info('{idx_name}');")
        col_names = tuple(col_row[2] for col_row in col_cursor.fetchall())

        indexes.append(IndexInfo(
            name=idx_name,
            unique=unique,
            origin=origin,
            columns=col_names,
        ))
    return tuple(indexes)


def get_foreign_keys(conn: sqlite3.Connection, table: str) -> tuple[ForeignKeyInfo, ...]:
    """Return foreign-key constraints for *table*.

    Args:
        conn:  An open SQLite connection.
        table: Name of the table to inspect.
    """
    cursor = conn.execute(f"PRAGMA foreign_key_list('{table}');")
    return tuple(
        ForeignKeyInfo(
            id=row[0],
            seq=row[1],
            table=row[2],
            from_col=row[3],
            to_col=row[4],
            on_update=row[5],
            on_delete=row[6],
        )
        for row in cursor.fetchall()
    )


def get_row_count(conn: sqlite3.Connection, table: str) -> int:
    """Return the current row count for *table*.

    Args:
        conn:  An open SQLite connection.
        table: Name of the table to count.
    """
    cursor = conn.execute(f"SELECT COUNT(*) FROM '{table}';")
    result = cursor.fetchone()
    return result[0] if result else 0


# ---------------------------------------------------------------------------
# High-level snapshot
# ---------------------------------------------------------------------------


def inspect_table(conn: sqlite3.Connection, table: str) -> TableSchema:
    """Build a complete :class:`TableSchema` snapshot for *table*.

    Args:
        conn:  An open SQLite connection.
        table: Name of the table to inspect.
    """
    return TableSchema(
        name=table,
        columns=get_columns(conn, table),
        indexes=get_indexes(conn, table),
        foreign_keys=get_foreign_keys(conn, table),
        row_count=get_row_count(conn, table),
    )


def inspect_schema(conn: sqlite3.Connection) -> dict[str, TableSchema]:
    """Return a ``{table_name: TableSchema}`` mapping for every user table.

    This is the primary entry-point used by the diff engine: call it once
    before the migration and once after, then compare the two snapshots.

    Args:
        conn: An open SQLite connection (read-only is fine).
    """
    tables = get_tables(conn)
    return {t: inspect_table(conn, t) for t in tables}

