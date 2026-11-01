"""
schemaguard/models.py
---------------------
Typed dataclasses representing every artefact produced during a migration
rehearsal run.  All fields are immutable (frozen=True) so that results can
be safely shared across Streamlit reruns without accidental mutation.

No business logic lives here — only data shapes and their invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Risk level assigned to a schema finding or invariant violation."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CheckStatus(str, Enum):
    """Outcome of an individual check (contract, invariant, …)."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Individual check results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaFinding:
    """A single observation about a schema element (table, column, index, …).

    Attributes:
        object_type: Kind of database object (e.g. ``"table"``, ``"column"``).
        object_name: Fully-qualified name of the affected object.
        finding:     Human-readable description of what was found.
        severity:    Risk level of this finding.
        suggestion:  Optional remediation hint surfaced in the report.
    """

    object_type: str
    object_name: str
    finding: str
    severity: Severity
    suggestion: str = ""

    def is_blocking(self) -> bool:
        """Return ``True`` if this finding should halt migration approval."""
        return self.severity in (Severity.ERROR, Severity.CRITICAL)


@dataclass(frozen=True)
class ContractResult:
    """Outcome of replaying a single read-only application query contract.

    A *contract* is a named SQL SELECT statement whose result shape (column
    names, row count bounds) must survive the migration unchanged.

    Attributes:
        contract_name:   Unique identifier for the contract.
        sql:             The SQL statement that was replayed.
        status:          Whether the contract passed, failed, or errored.
        row_count_pre:   Row count returned **before** the migration.
        row_count_post:  Row count returned **after** the migration.
        columns_pre:     Column names returned **before** the migration.
        columns_post:    Column names returned **after** the migration.
        error_message:   Populated only when ``status`` is ``ERROR``.
        elapsed_ms:      Wall-clock time (milliseconds) for the post run.
    """

    contract_name: str
    sql: str
    status: CheckStatus
    row_count_pre: int = 0
    row_count_post: int = 0
    columns_pre: tuple[str, ...] = field(default_factory=tuple)
    columns_post: tuple[str, ...] = field(default_factory=tuple)
    error_message: str = ""
    elapsed_ms: float = 0.0

    def columns_changed(self) -> bool:
        """Return ``True`` if the result set columns differ post-migration."""
        return self.columns_pre != self.columns_post

    def row_count_delta(self) -> int:
        """Signed difference in row count (post − pre)."""
        return self.row_count_post - self.row_count_pre


@dataclass(frozen=True)
class InvariantResult:
    """Outcome of evaluating a single SQL invariant assertion.

    An *invariant* is a SQL expression expected to evaluate to a truthy value
    (non-zero, non-NULL) after the migration, e.g.
    ``SELECT COUNT(*) = 0 FROM orders WHERE total < 0``.

    Attributes:
        invariant_name: Unique identifier for the invariant.
        sql:            The SQL expression evaluated in the sandbox.
        status:         Whether the invariant held, was violated, or errored.
        result_value:   The raw value returned by SQLite.
        error_message:  Populated only when ``status`` is ``ERROR``.
    """

    invariant_name: str
    sql: str
    status: CheckStatus
    result_value: Any = None
    error_message: str = ""

    def held(self) -> bool:
        """Return ``True`` if the invariant evaluated to a truthy value."""
        return self.status == CheckStatus.PASSED


@dataclass(frozen=True)
class SchemaDiffResult:
    """Structural diff between the pre- and post-migration schema.

    Attributes:
        tables_added:    Tables present **only** after migration.
        tables_removed:  Tables present **only** before migration.
        tables_modified: Tables present in both but with structural changes.
        columns_added:   Mapping of ``table → [column_name, …]`` for new cols.
        columns_removed: Mapping of ``table → [column_name, …]`` for dropped cols.
        columns_modified:Mapping of ``table → {col: (old_type, new_type)}`` for type changes.
        indexes_added:   Index names added by the migration.
        indexes_removed: Index names removed by the migration.
        row_count_deltas:Mapping of ``table → (pre_count, post_count)``.
    """

    tables_added: tuple[str, ...] = field(default_factory=tuple)
    tables_removed: tuple[str, ...] = field(default_factory=tuple)
    tables_modified: tuple[str, ...] = field(default_factory=tuple)
    columns_added: dict[str, list[str]] = field(default_factory=dict)
    columns_removed: dict[str, list[str]] = field(default_factory=dict)
    columns_modified: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)
    indexes_added: tuple[str, ...] = field(default_factory=tuple)
    indexes_removed: tuple[str, ...] = field(default_factory=tuple)
    row_count_deltas: dict[str, tuple[int, int]] = field(default_factory=dict)

    def has_destructive_changes(self) -> bool:
        """Return ``True`` if any columns or tables were removed."""
        return bool(self.tables_removed or self.columns_removed)

    def is_clean(self) -> bool:
        """Return ``True`` when no structural changes were detected at all."""
        return not any([
            self.tables_added,
            self.tables_removed,
            self.tables_modified,
            self.indexes_added,
            self.indexes_removed,
        ])


# ---------------------------------------------------------------------------
# Top-level aggregate result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MigrationResult:
    """Aggregated result of a complete migration rehearsal run.

    This is the single object passed to the report generator after all checks
    have been executed against the sandbox.

    Attributes:
        source_db_path:    Absolute path to the **original** (read-only) DB.
        sandbox_db_path:   Absolute path to the sandboxed copy.
        migration_sql:     The full migration SQL that was rehearsed.
        migration_applied: Whether the migration DDL was executed without error.
        schema_diff:       Structural diff between pre- and post-migration.
        schema_findings:   All schema-level observations and warnings.
        contract_results:  Results for each replayed query contract.
        invariant_results: Results for each SQL invariant assertion.
        run_timestamp_utc: ISO-8601 UTC timestamp when the run started.
        elapsed_total_ms:  Total wall-clock time for the entire rehearsal.
        migration_error:   Error message if the migration DDL itself failed.
    """

    source_db_path: str
    sandbox_db_path: str
    migration_sql: str
    migration_applied: bool
    schema_diff: SchemaDiffResult
    schema_findings: tuple[SchemaFinding, ...] = field(default_factory=tuple)
    contract_results: tuple[ContractResult, ...] = field(default_factory=tuple)
    invariant_results: tuple[InvariantResult, ...] = field(default_factory=tuple)
    run_timestamp_utc: str = ""
    elapsed_total_ms: float = 0.0
    migration_error: str = ""

    # ------------------------------------------------------------------
    # Convenience aggregations
    # ------------------------------------------------------------------

    def overall_passed(self) -> bool:
        """Return ``True`` only when every check passed and migration applied."""
        if not self.migration_applied:
            return False
        contracts_ok = all(r.status == CheckStatus.PASSED for r in self.contract_results)
        invariants_ok = all(r.status == CheckStatus.PASSED for r in self.invariant_results)
        findings_ok = not any(f.is_blocking() for f in self.schema_findings)
        return contracts_ok and invariants_ok and findings_ok

    def blocking_findings(self) -> list[SchemaFinding]:
        """Return only the findings that block migration approval."""
        return [f for f in self.schema_findings if f.is_blocking()]

    def failed_contracts(self) -> list[ContractResult]:
        """Return only the contracts that did not pass."""
        return [r for r in self.contract_results if r.status != CheckStatus.PASSED]

    def failed_invariants(self) -> list[InvariantResult]:
        """Return only the invariants that did not hold."""
        return [r for r in self.invariant_results if r.status != CheckStatus.PASSED]

