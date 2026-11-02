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
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Risk level assigned to a schema finding or invariant violation."""

    CRITICAL = "critical"
    HIGH = "high"
    ERROR = "error"
    MODERATE = "moderate"
    WARNING = "warning"
    LOW = "low"
    INFO = "info"


class CheckStatus(str, Enum):
    """Outcome of an individual check (contract, invariant, …)."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PASS = "PASS"
    FAIL = "FAIL"
    REJECTED = "REJECTED"


class ContractStatus(str, Enum):
    """Outcome of an application query contract check."""

    PASS = "PASS"
    FAIL = "FAIL"
    REJECTED = "REJECTED"


class ContractType(str, Enum):
    """Classification of an application query contract."""

    OLD_APP = "OLD_APP"
    NEW_APP = "NEW_APP"


# ---------------------------------------------------------------------------
# Individual check results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaFinding:
    """A finding from static SQL analysis or dynamic schema inspection.

    Attributes:
        rule_id:             Unique rule identifier (e.g. ``"SG-ST-001"``).
        severity:            Risk level (CRITICAL, HIGH, MODERATE, LOW, INFO).
        title:               Short descriptive title of the finding.
        explanation:         Detailed technical explanation of the issue.
        evidence:            Raw SQL snippet or statement text.
        statement_index:     Zero-based position of the statement in the migration.
        human_review_action: Recommended verification or review action.
        object_type:         Target object kind (e.g. ``"table"``, ``"column"``).
        object_name:         Name of the affected database object.
        finding:             Human-readable summary (defaults to title + explanation).
        suggestion:          Remediation advice (defaults to human_review_action).
        is_static:           True if identified by static analysis.
        is_destructive:      True if this finding represents a destructive change.
    """

    rule_id: str = ""
    severity: Severity = Severity.WARNING
    title: str = ""
    explanation: str = ""
    evidence: str = ""
    statement_index: int = 0
    human_review_action: str = ""
    object_type: str = ""
    object_name: str = ""
    finding: str = ""
    suggestion: str = ""
    is_static: bool = True
    is_destructive: bool = True

    def __post_init__(self) -> None:
        """Derive legacy/summary fields if not explicitly provided."""
        if not self.finding and (self.title or self.explanation):
            object.__setattr__(
                self,
                "finding",
                f"{self.title}: {self.explanation}" if self.title and self.explanation else (self.title or self.explanation),
            )
        if not self.suggestion and self.human_review_action:
            object.__setattr__(self, "suggestion", self.human_review_action)
        if not self.title and self.finding:
            object.__setattr__(self, "title", self.finding)
        if not self.human_review_action and self.suggestion:
            object.__setattr__(self, "human_review_action", self.suggestion)

    def is_blocking(self) -> bool:
        """Return ``True`` if this finding should halt migration approval."""
        return self.severity in (Severity.CRITICAL, Severity.HIGH, Severity.ERROR)


# Alias for explicit static analysis code clarity
StaticFinding = SchemaFinding


@dataclass(frozen=True)
class ContractResult:
    """Outcome of replaying a single read-only application query contract.

    Attributes:
        name:              Unique identifier / name of the contract.
        contract_type:     ContractType.OLD_APP or ContractType.NEW_APP.
        status:            ContractStatus.PASS, FAIL, or REJECTED.
        sql_statement:     The SQL query string that was executed.
        execution_time_ms: Wall-clock query execution time in milliseconds.
        error_message:     Error message if status is FAIL or REJECTED.
        column_names:      Tuple of result column names (if passed).
        row_count_post:    Row count returned post-migration.
        row_count_pre:     Row count returned pre-migration (if replayed).
        columns_pre:       Column names returned before migration (if replayed).
        contract_name:     Backward-compatibility alias for name.
        sql:               Backward-compatibility alias for sql_statement.
        elapsed_ms:        Backward-compatibility alias for execution_time_ms.
        columns_post:      Backward-compatibility alias for column_names.
    """

    name: str = ""
    contract_type: ContractType | str = ContractType.OLD_APP
    status: ContractStatus | CheckStatus | str = ContractStatus.PASS
    sql_statement: str = ""
    execution_time_ms: float = 0.0
    error_message: str = ""
    column_names: tuple[str, ...] = field(default_factory=tuple)
    row_count_post: int = 0
    row_count_pre: int = 0
    columns_pre: tuple[str, ...] = field(default_factory=tuple)
    contract_name: str = ""
    sql: str = ""
    elapsed_ms: float = 0.0
    columns_post: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Synchronize primary and alias fields for full compatibility."""
        n = self.name or self.contract_name
        object.__setattr__(self, "name", n)
        object.__setattr__(self, "contract_name", n)

        s = self.sql_statement or self.sql
        object.__setattr__(self, "sql_statement", s)
        object.__setattr__(self, "sql", s)

        t = self.execution_time_ms or self.elapsed_ms
        object.__setattr__(self, "execution_time_ms", t)
        object.__setattr__(self, "elapsed_ms", t)

        cols = tuple(self.column_names) if self.column_names else tuple(self.columns_post)
        object.__setattr__(self, "column_names", cols)
        object.__setattr__(self, "columns_post", cols)

    def columns_changed(self) -> bool:
        """Return ``True`` if the result set columns differ post-migration."""
        if not self.columns_pre:
            return False
        return self.columns_pre != self.column_names

    def row_count_delta(self) -> int:
        """Signed difference in row count (post − pre)."""
        return self.row_count_post - self.row_count_pre


class InvariantStatus(str, Enum):
    """Outcome of a data invariant evaluation."""

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class InvariantResult:
    """Outcome of evaluating a single SQL invariant assertion.

    An invariant is a read-only query that checks for bad or violating data.
    Rule: The query must return ZERO rows to PASS.

    Attributes:
        name:                 Unique name/title for the invariant.
        sql:                  The SQL assertion query evaluated in the sandbox.
        status:               PASS (0 violating rows), FAIL (>= 1 rows), or ERROR.
        violating_rows_count: Number of rows returned violating the invariant.
        error_message:        Populated only when status is ERROR.
        execution_time_ms:    Wall-clock query execution time in milliseconds.
        sample_violations:    Sample of violating rows (as column-value mappings).
        invariant_name:       Backward-compatibility alias for name.
        result_value:         Backward-compatibility alias for violating_rows_count.
    """

    name: str = ""
    sql: str = ""
    status: InvariantStatus | CheckStatus | str = InvariantStatus.PASS
    violating_rows_count: int = 0
    error_message: str = ""
    execution_time_ms: float = 0.0
    sample_violations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    invariant_name: str = ""
    result_value: Any = None

    def __post_init__(self) -> None:
        """Synchronize primary and alias fields for full compatibility."""
        n = self.name or self.invariant_name
        object.__setattr__(self, "name", n)
        object.__setattr__(self, "invariant_name", n)

        if self.result_value is None and self.violating_rows_count:
            object.__setattr__(self, "result_value", self.violating_rows_count)
        elif self.result_value is not None and not self.violating_rows_count and isinstance(self.result_value, int):
            object.__setattr__(self, "violating_rows_count", self.result_value)

    def held(self) -> bool:
        """Return ``True`` if the invariant passed (zero violating rows)."""
        return (
            self.status in (InvariantStatus.PASS, CheckStatus.PASSED, "PASS", "passed")
            and self.violating_rows_count == 0
        )


@dataclass(frozen=True)
class SchemaDiffResult:
    """Structural diff between the pre- and post-migration schema.

    Attributes:
        tables_added:           Tables present **only** after migration.
        tables_removed:         Tables present **only** before migration.
        tables_modified:        Tables present in both but with structural changes.
        columns_added:          Mapping of ``table → [column_name, …]`` for new cols.
        columns_removed:        Mapping of ``table → [column_name, …]`` for dropped cols.
        columns_modified:       Mapping of ``table → {col: (old_type, new_type)}`` for type changes.
        indexes_added:          Index names added by the migration.
        indexes_removed:        Index names removed by the migration.
        row_count_deltas:       Mapping of ``table → (pre_count, post_count)``.
        primary_keys_modified:  Mapping of ``table → (pre_pks, post_pks)``.
        foreign_keys_added:     Mapping of ``table → [fk_descriptions]``.
        foreign_keys_removed:   Mapping of ``table → [fk_descriptions]``.
        foreign_keys_modified:  Mapping of ``table → [fk_descriptions]``.
        indexes_modified:       Mapping of ``table → [index_names]``.
        column_details_altered: Mapping of ``table → {col: {attr: (old, new)}}``.
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
    primary_keys_modified: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = field(default_factory=dict)
    foreign_keys_added: dict[str, list[str]] = field(default_factory=dict)
    foreign_keys_removed: dict[str, list[str]] = field(default_factory=dict)
    foreign_keys_modified: dict[str, list[str]] = field(default_factory=dict)
    indexes_modified: dict[str, list[str]] = field(default_factory=dict)
    column_details_altered: dict[str, dict[str, dict[str, tuple[Any, Any]]]] = field(default_factory=dict)

    def has_destructive_changes(self) -> bool:
        """Return ``True`` if any columns or tables were removed or rows dropped unexpectedly."""
        has_dropped_objects = bool(self.tables_removed or self.columns_removed)
        has_row_drops = any(post < pre for pre, post in self.row_count_deltas.values())
        return has_dropped_objects or has_row_drops

    def is_clean(self) -> bool:
        """Return ``True`` when no structural changes were detected at all."""
        return not any([
            self.tables_added,
            self.tables_removed,
            self.tables_modified,
            self.indexes_added,
            self.indexes_removed,
            self.foreign_keys_added,
            self.foreign_keys_removed,
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
        contracts_ok = all(
            r.status in (ContractStatus.PASS, CheckStatus.PASSED, "PASS", "passed")
            for r in self.contract_results
        )
        invariants_ok = all(
            r.status in (InvariantStatus.PASS, CheckStatus.PASSED, "PASS", "passed") and r.held()
            for r in self.invariant_results
        )
        findings_ok = not any(f.is_blocking() for f in self.schema_findings)
        return contracts_ok and invariants_ok and findings_ok

    def blocking_findings(self) -> list[SchemaFinding]:
        """Return only the findings that block migration approval."""
        return [f for f in self.schema_findings if f.is_blocking()]

    def failed_contracts(self) -> list[ContractResult]:
        """Return only the contracts that did not pass."""
        return [
            r for r in self.contract_results
            if r.status not in (ContractStatus.PASS, CheckStatus.PASSED, "PASS", "passed")
        ]

    def failed_invariants(self) -> list[InvariantResult]:
        """Return only the invariants that did not hold."""
        return [
            r for r in self.invariant_results
            if r.status not in (InvariantStatus.PASS, CheckStatus.PASSED, "PASS", "passed") or not r.held()
        ]

