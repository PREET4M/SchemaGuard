"""
schemaguard/core/data_profiler.py
--------------------------------
Table row count profiling and anomaly detection before and after migrations.

Tracks:
  - Exact row counts before and after migration
  - Missing (dropped) tables
  - Newly created tables
  - Unexpected row reductions/drops (post_count < pre_count)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from schemaguard.core.schema_inspector import get_row_count, get_tables


@dataclass(frozen=True)
class TableRowDelta:
    """Row count comparison metrics for a single table.

    Attributes:
        table_name:       Name of the database table.
        pre_count:        Row count before migration (None if newly created).
        post_count:       Row count after migration (None if dropped).
        delta:            post_count - pre_count (None if table dropped/created).
        status:           "unchanged", "increased", "decreased", "dropped", "created".
        is_row_drop:      True if table exists in both and post_count < pre_count.
    """

    table_name: str
    pre_count: int | None
    post_count: int | None
    delta: int | None
    status: str
    is_row_drop: bool


@dataclass(frozen=True)
class DataProfileResult:
    """Comprehensive data profile comparing pre- and post-migration states.

    Attributes:
        table_deltas:             Mapping of table_name -> TableRowDelta.
        row_count_deltas:         Mapping of table_name -> (pre_count, post_count).
        missing_tables:           Tables present in pre-migration but absent post-migration.
        created_tables:           Tables created in post-migration.
        tables_with_dropped_rows: Tables present in both with fewer rows post-migration.
        total_rows_pre:           Sum of rows across all pre-migration tables.
        total_rows_post:          Sum of rows across all post-migration tables.
        total_delta:              total_rows_post - total_rows_pre.
        has_unexpected_drops:     True if any tables were dropped or lost rows.
    """

    table_deltas: dict[str, TableRowDelta]
    row_count_deltas: dict[str, tuple[int, int]]
    missing_tables: tuple[str, ...]
    created_tables: tuple[str, ...]
    tables_with_dropped_rows: tuple[str, ...]
    total_rows_pre: int
    total_rows_post: int
    total_delta: int
    has_unexpected_drops: bool


def get_table_row_count(conn: sqlite3.Connection, table_name: str) -> int:
    """Return the total number of rows in table_name."""
    return get_row_count(conn, table_name)


def profile_database_rows(conn: sqlite3.Connection) -> dict[str, int]:
    """Capture row counts for all non-system tables in conn.

    Args:
        conn: Open SQLite connection.

    Returns:
        Mapping of table_name -> row_count.
    """
    tables = get_tables(conn)
    return {table: get_row_count(conn, table) for table in tables}


def compute_data_profile(
    pre_counts: dict[str, int],
    post_counts: dict[str, int],
) -> DataProfileResult:
    """Compute row-level diffs and detect missing tables or unexpected row drops.

    Args:
        pre_counts:  Table row counts before migration.
        post_counts: Table row counts after migration.

    Returns:
        A DataProfileResult object.
    """
    all_tables = sorted(set(pre_counts.keys()) | set(post_counts.keys()))

    table_deltas: dict[str, TableRowDelta] = {}
    row_count_deltas: dict[str, tuple[int, int]] = {}
    missing_tables: list[str] = []
    created_tables: list[str] = []
    tables_with_dropped_rows: list[str] = []

    for table in all_tables:
        in_pre = table in pre_counts
        in_post = table in post_counts

        pre_c = pre_counts.get(table)
        post_c = post_counts.get(table)

        row_count_deltas[table] = (pre_c if pre_c is not None else 0, post_c if post_c is not None else 0)

        if in_pre and not in_post:
            missing_tables.append(table)
            table_deltas[table] = TableRowDelta(
                table_name=table,
                pre_count=pre_c,
                post_count=None,
                delta=None,
                status="dropped",
                is_row_drop=True,
            )
        elif in_post and not in_pre:
            created_tables.append(table)
            table_deltas[table] = TableRowDelta(
                table_name=table,
                pre_count=None,
                post_count=post_c,
                delta=None,
                status="created",
                is_row_drop=False,
            )
        else:
            # Present in both
            assert pre_c is not None and post_c is not None
            delta = post_c - pre_c
            is_drop = post_c < pre_c
            if is_drop:
                tables_with_dropped_rows.append(table)
                status = "decreased"
            elif post_c > pre_c:
                status = "increased"
            else:
                status = "unchanged"

            table_deltas[table] = TableRowDelta(
                table_name=table,
                pre_count=pre_c,
                post_count=post_c,
                delta=delta,
                status=status,
                is_row_drop=is_drop,
            )

    total_pre = sum(pre_counts.values())
    total_post = sum(post_counts.values())
    total_delta = total_post - total_pre
    has_drops = bool(missing_tables or tables_with_dropped_rows)

    return DataProfileResult(
        table_deltas=table_deltas,
        row_count_deltas=row_count_deltas,
        missing_tables=tuple(missing_tables),
        created_tables=tuple(created_tables),
        tables_with_dropped_rows=tuple(tables_with_dropped_rows),
        total_rows_pre=total_pre,
        total_rows_post=total_post,
        total_delta=total_delta,
        has_unexpected_drops=has_drops,
    )


def profile_connections(
    pre_conn: sqlite3.Connection,
    post_conn: sqlite3.Connection,
) -> DataProfileResult:
    """Capture row counts from both connections and compute the data profile."""
    pre_counts = profile_database_rows(pre_conn)
    post_counts = profile_database_rows(post_conn)
    return compute_data_profile(pre_counts, post_counts)


__all__ = [
    "TableRowDelta",
    "DataProfileResult",
    "get_table_row_count",
    "profile_database_rows",
    "compute_data_profile",
    "profile_connections",
]

