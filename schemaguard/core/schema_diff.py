"""
schemaguard/core/schema_diff.py
-------------------------------
Structural schema diff engine comparing baseline and post-migration states.

Detects:
  - Added, removed, and structurally modified tables
  - Added and removed columns per table
  - Altered column types, default values, and NOT NULL constraints
  - Modified primary keys
  - Added, removed, and modified indexes
  - Added, removed, and modified foreign keys
  - Table-level row count deltas
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from schemaguard.core.schema_inspector import (
    ForeignKeyInfo,
    IndexInfo,
    TableSchema,
    inspect_schema,
)
from schemaguard.models import SchemaDiffResult


def _format_fk(fk: ForeignKeyInfo) -> str:
    """Format a foreign key constraint as a readable string."""
    return f"{fk.from_col} -> {fk.table}({fk.to_col})"


def diff_schemas(
    baseline: dict[str, TableSchema],
    post: dict[str, TableSchema],
) -> SchemaDiffResult:
    """Compare baseline schema snapshot with post-migration schema snapshot.

    Args:
        baseline: Schema mapping {table_name: TableSchema} before migration.
        post:     Schema mapping {table_name: TableSchema} after migration.

    Returns:
        A populated SchemaDiffResult frozen dataclass.
    """
    tables_added = tuple(sorted(set(post.keys()) - set(baseline.keys())))
    tables_removed = tuple(sorted(set(baseline.keys()) - set(post.keys())))
    common_tables = sorted(set(baseline.keys()) & set(post.keys()))

    tables_modified: list[str] = []
    columns_added: dict[str, list[str]] = {}
    columns_removed: dict[str, list[str]] = {}
    columns_modified: dict[str, dict[str, tuple[str, str]]] = {}
    column_details_altered: dict[str, dict[str, dict[str, tuple[Any, Any]]]] = {}
    primary_keys_modified: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    foreign_keys_added: dict[str, list[str]] = {}
    foreign_keys_removed: dict[str, list[str]] = {}
    foreign_keys_modified: dict[str, list[str]] = {}
    indexes_modified: dict[str, list[str]] = {}

    # Global indexes (excluding auto-indexes)
    all_pre_indexes: dict[str, IndexInfo] = {}
    for t_schema in baseline.values():
        for idx in t_schema.indexes:
            if idx.name and not idx.name.startswith("sqlite_autoindex"):
                all_pre_indexes[idx.name] = idx

    all_post_indexes: dict[str, IndexInfo] = {}
    for t_schema in post.values():
        for idx in t_schema.indexes:
            if idx.name and not idx.name.startswith("sqlite_autoindex"):
                all_post_indexes[idx.name] = idx

    indexes_added = tuple(sorted(set(all_post_indexes.keys()) - set(all_pre_indexes.keys())))
    indexes_removed = tuple(sorted(set(all_pre_indexes.keys()) - set(all_post_indexes.keys())))

    # Inspect common tables
    for table in common_tables:
        table_has_changes = False
        base_t = baseline[table]
        post_t = post[table]

        # 1. Columns Added / Removed / Altered
        base_cols = {c.name: c for c in base_t.columns}
        post_cols = {c.name: c for c in post_t.columns}

        added_cols = [c for c in post_cols if c not in base_cols]
        removed_cols = [c for c in base_cols if c not in post_cols]

        if added_cols:
            columns_added[table] = added_cols
            table_has_changes = True

        if removed_cols:
            columns_removed[table] = removed_cols
            table_has_changes = True

        # Check altered properties of common columns
        for col_name in sorted(set(base_cols.keys()) & set(post_cols.keys())):
            c_pre = base_cols[col_name]
            c_post = post_cols[col_name]
            diffs: dict[str, tuple[Any, Any]] = {}

            if c_pre.col_type.upper() != c_post.col_type.upper():
                diffs["type"] = (c_pre.col_type, c_post.col_type)

            if c_pre.notnull != c_post.notnull:
                diffs["notnull"] = (c_pre.notnull, c_post.notnull)

            if c_pre.default_value != c_post.default_value:
                diffs["default_value"] = (c_pre.default_value, c_post.default_value)

            if c_pre.pk != c_post.pk:
                diffs["pk"] = (c_pre.pk, c_post.pk)

            if diffs:
                table_has_changes = True
                if table not in column_details_altered:
                    column_details_altered[table] = {}
                column_details_altered[table][col_name] = diffs

                if table not in columns_modified:
                    columns_modified[table] = {}
                # Legacy compatibility mapping: {col: (old_type, new_type)}
                old_t = diffs.get("type", (c_pre.col_type, c_post.col_type))[0]
                new_t = diffs.get("type", (c_pre.col_type, c_post.col_type))[1]
                columns_modified[table][col_name] = (old_t, new_t)

        # 2. Primary Keys Modified
        pre_pk = tuple(c.name for c in sorted(base_t.columns, key=lambda x: x.pk) if c.pk > 0)
        post_pk = tuple(c.name for c in sorted(post_t.columns, key=lambda x: x.pk) if c.pk > 0)
        if pre_pk != post_pk:
            primary_keys_modified[table] = (pre_pk, post_pk)
            table_has_changes = True

        # 3. Foreign Keys Modified
        base_fks = {_format_fk(fk): fk for fk in base_t.foreign_keys}
        post_fks = {_format_fk(fk): fk for fk in post_t.foreign_keys}

        added_fks = [fk_str for fk_str in post_fks if fk_str not in base_fks]
        removed_fks = [fk_str for fk_str in base_fks if fk_str not in post_fks]

        if added_fks:
            foreign_keys_added[table] = added_fks
            table_has_changes = True
        if removed_fks:
            foreign_keys_removed[table] = removed_fks
            table_has_changes = True

        # 4. Table Indexes Modified
        base_idx_map = {idx.name: idx for idx in base_t.indexes if idx.name and not idx.name.startswith("sqlite_autoindex")}
        post_idx_map = {idx.name: idx for idx in post_t.indexes if idx.name and not idx.name.startswith("sqlite_autoindex")}

        mod_indexes: list[str] = []
        for idx_name in set(base_idx_map.keys()) & set(post_idx_map.keys()):
            b_idx = base_idx_map[idx_name]
            p_idx = post_idx_map[idx_name]
            if b_idx.columns != p_idx.columns or b_idx.unique != p_idx.unique:
                mod_indexes.append(idx_name)

        if mod_indexes:
            indexes_modified[table] = mod_indexes
            table_has_changes = True

        # Check if any added/removed index belonged to this table
        table_idx_added = [i for i in post_idx_map if i not in base_idx_map]
        table_idx_removed = [i for i in base_idx_map if i not in post_idx_map]
        if table_idx_added or table_idx_removed:
            table_has_changes = True

        if table_has_changes:
            tables_modified.append(table)

    # 5. Row count deltas for all tables
    row_count_deltas: dict[str, tuple[int, int]] = {}
    all_table_names = sorted(set(baseline.keys()) | set(post.keys()))
    for table in all_table_names:
        pre_cnt = baseline[table].row_count if table in baseline else 0
        post_cnt = post[table].row_count if table in post else 0
        row_count_deltas[table] = (pre_cnt, post_cnt)

    return SchemaDiffResult(
        tables_added=tables_added,
        tables_removed=tables_removed,
        tables_modified=tuple(sorted(tables_modified)),
        columns_added=columns_added,
        columns_removed=columns_removed,
        columns_modified=columns_modified,
        indexes_added=indexes_added,
        indexes_removed=indexes_removed,
        row_count_deltas=row_count_deltas,
        primary_keys_modified=primary_keys_modified,
        foreign_keys_added=foreign_keys_added,
        foreign_keys_removed=foreign_keys_removed,
        foreign_keys_modified=foreign_keys_modified,
        indexes_modified=indexes_modified,
        column_details_altered=column_details_altered,
    )


def diff_connections(
    pre_conn: sqlite3.Connection,
    post_conn: sqlite3.Connection,
) -> SchemaDiffResult:
    """Introspect both connections and compute the schema diff."""
    baseline_schema = inspect_schema(pre_conn)
    post_schema = inspect_schema(post_conn)
    return diff_schemas(baseline_schema, post_schema)


def diff_databases(
    pre_db_path: Path | str,
    post_db_path: Path | str,
) -> SchemaDiffResult:
    """Connect to both database files (read-only) and compute the schema diff."""
    pre_conn = sqlite3.connect(f"file:{Path(pre_db_path).resolve().as_posix()}?mode=ro", uri=True)
    post_conn = sqlite3.connect(f"file:{Path(post_db_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        return diff_connections(pre_conn, post_conn)
    finally:
        pre_conn.close()
        post_conn.close()


__all__ = [
    "diff_schemas",
    "diff_connections",
    "diff_databases",
]

