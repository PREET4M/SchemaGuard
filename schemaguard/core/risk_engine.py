"""
schemaguard/core/risk_engine.py
-------------------------------
Evidence-backed risk evaluation engine for database migration rehearsals.

Categorical Severity Rules:
  - CRITICAL: Migration execution failed OR an OLD_APP query contract failed.
  - HIGH:     Data invariant failed OR table dropped OR material column dropped.
  - MODERATE: Potentially risky static finding OR NEW_APP query contract failed.
  - LOW:      No configured checks failed. Display exact label:
              "No configured checks failed" (never say "guaranteed safe").

Heuristic Risk Score (0-100, capped at 100):
  - Migration execution failure: 100
  - Dropped table:               35 each
  - Old app contract failure:    30 each
  - Invariant failure:           25 each
  - Dropped column:              20 each
  - Row reduction:               15
  - New app contract failure:    15 each
  - Risky static finding:        10 each

Rule: Never let a low numerical score override a concrete CRITICAL finding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Iterable

from schemaguard.models import (
    ContractResult,
    ContractStatus,
    ContractType,
    InvariantResult,
    InvariantStatus,
    MigrationResult,
    SchemaDiffResult,
    SchemaFinding,
    Severity,
)

LABEL_LOW_RISK: Final[str] = "No configured checks failed"
LABEL_MODERATE_RISK: Final[str] = "Moderate Risk — Static warnings or new contract issues"
LABEL_HIGH_RISK: Final[str] = "High Risk — Data invariants violated or schema objects dropped"
LABEL_CRITICAL_RISK: Final[str] = "Critical Risk — Migration execution or existing contract broken"


@dataclass(frozen=True)
class RiskFactor:
    """Individual evidence factor contributing to risk severity and score."""

    category: str
    severity: Severity
    points: int
    description: str


@dataclass(frozen=True)
class RiskAssessment:
    """Consolidated risk assessment generated from rehearsal evidence.

    Attributes:
        severity:         Overall categorical severity (CRITICAL, HIGH, MODERATE, LOW).
        risk_score:       Heuristic score between 0 and 100.
        label:            Descriptive summary verdict label.
        reasons:          Tuple of specific human-readable finding justifications.
        factors:          Tuple of itemized RiskFactor records.
        can_auto_approve: True only if severity is LOW and score is 0.
    """

    severity: Severity
    risk_score: int
    label: str
    reasons: tuple[str, ...]
    factors: tuple[RiskFactor, ...]
    can_auto_approve: bool


def assess_risk(
    migration_result: MigrationResult | None = None,
    *,
    migration_succeeded: bool = True,
    contract_results: Iterable[ContractResult] = (),
    invariant_results: Iterable[InvariantResult] = (),
    schema_diff: SchemaDiffResult | None = None,
    static_findings: Iterable[SchemaFinding] = (),
    row_count_reduction: bool = False,
) -> RiskAssessment:
    """Evaluate all migration rehearsal evidence and compute overall severity and risk score.

    Can be called directly with a MigrationResult instance or with individual keyword arguments.

    Args:
        migration_result:    Complete MigrationResult object (if available).
        migration_succeeded: Explicit migration execution status.
        contract_results:    Collection of replayed ContractResult records.
        invariant_results:   Collection of evaluated InvariantResult records.
        schema_diff:         Schema diff snapshot.
        static_findings:     Static analysis warnings from SQLGlot.
        row_count_reduction: True if any existing table experienced a net row drop.

    Returns:
        A deterministic RiskAssessment object.
    """
    # 1. Unpack from migration_result if supplied
    if migration_result is not None:
        migration_succeeded = migration_result.migration_applied
        contract_results = migration_result.contract_results
        invariant_results = migration_result.invariant_results
        schema_diff = migration_result.schema_diff
        static_findings = migration_result.schema_findings
        if schema_diff is not None:
            row_count_reduction = any(
                post < pre for pre, post in schema_diff.row_count_deltas.values()
            )

    factors: list[RiskFactor] = []
    reasons: list[str] = []

    # ------------------------------------------------------------------
    # Category 1: Migration Execution
    # ------------------------------------------------------------------
    if not migration_succeeded:
        factors.append(
            RiskFactor(
                category="migration_execution",
                severity=Severity.CRITICAL,
                points=100,
                description="Migration DDL/DML failed to execute against the sandbox database.",
            )
        )
        reasons.append("Migration DDL execution failed.")

    # ------------------------------------------------------------------
    # Category 2: Application Query Contracts
    # ------------------------------------------------------------------
    old_app_failures = 0
    new_app_failures = 0

    for c in contract_results:
        is_pass = c.status in (ContractStatus.PASS, "PASS", "passed")
        if not is_pass:
            is_old = str(c.contract_type).upper().endswith("OLD_APP") or c.contract_type == ContractType.OLD_APP
            if is_old:
                old_app_failures += 1
                factors.append(
                    RiskFactor(
                        category="old_app_contract",
                        severity=Severity.CRITICAL,
                        points=30,
                        description=f"Existing application contract '{c.name}' failed post-migration: {c.error_message}",
                    )
                )
                reasons.append(f"Existing contract '{c.name}' failed: {c.error_message or 'execution error'}")
            else:
                new_app_failures += 1
                factors.append(
                    RiskFactor(
                        category="new_app_contract",
                        severity=Severity.MODERATE,
                        points=15,
                        description=f"New application contract '{c.name}' failed post-migration: {c.error_message}",
                    )
                )
                reasons.append(f"New contract '{c.name}' failed: {c.error_message or 'execution error'}")

    # ------------------------------------------------------------------
    # Category 3: Data Invariants
    # ------------------------------------------------------------------
    invariant_failures = 0
    for inv in invariant_results:
        is_held = inv.held()
        if not is_held:
            invariant_failures += 1
            factors.append(
                RiskFactor(
                    category="data_invariant",
                    severity=Severity.HIGH,
                    points=25,
                    description=(
                        f"Data invariant '{inv.name}' violated "
                        f"({inv.violating_rows_count} violating rows): {inv.error_message}"
                    ),
                )
            )
            reasons.append(
                f"Data invariant '{inv.name}' violated with {inv.violating_rows_count} bad row(s)."
            )

    # ------------------------------------------------------------------
    # Category 4: Structural Schema Diff
    # ------------------------------------------------------------------
    dropped_tables_count = 0
    dropped_columns_count = 0

    if schema_diff is not None:
        for t in schema_diff.tables_removed:
            dropped_tables_count += 1
            factors.append(
                RiskFactor(
                    category="dropped_table",
                    severity=Severity.HIGH,
                    points=35,
                    description=f"Table '{t}' was permanently dropped by the migration.",
                )
            )
            reasons.append(f"Table '{t}' dropped.")

        for t, cols in schema_diff.columns_removed.items():
            for col in cols:
                dropped_columns_count += 1
                factors.append(
                    RiskFactor(
                        category="dropped_column",
                        severity=Severity.HIGH,
                        points=20,
                        description=f"Column '{t}.{col}' was dropped by the migration.",
                    )
                )
                reasons.append(f"Column '{t}.{col}' dropped.")

    # ------------------------------------------------------------------
    # Category 5: Unexpected Row Reduction
    # ------------------------------------------------------------------
    if row_count_reduction:
        factors.append(
            RiskFactor(
                category="row_reduction",
                severity=Severity.HIGH,
                points=15,
                description="One or more existing tables experienced an unexpected reduction in row count.",
            )
        )
        reasons.append("Unexpected row count reduction detected.")

    # ------------------------------------------------------------------
    # Category 6: Risky Static Findings
    # ------------------------------------------------------------------
    risky_static_count = 0
    for sf in static_findings:
        if sf.is_blocking() or sf.is_destructive:
            risky_static_count += 1
            factors.append(
                RiskFactor(
                    category="static_finding",
                    severity=Severity.MODERATE,
                    points=10,
                    description=f"Static analysis warning [{sf.rule_id}]: {sf.title}",
                )
            )
            reasons.append(f"Static analysis warning [{sf.rule_id}]: {sf.title}")

    # ------------------------------------------------------------------
    # Compute Categorical Severity
    # ------------------------------------------------------------------
    # CRITICAL: Migration execution failed OR an OLD_APP query contract failed.
    # HIGH:     Data invariant failed OR table dropped OR material column dropped.
    # MODERATE: Potentially risky static finding OR NEW_APP query contract failed.
    # LOW:      No configured checks failed.
    if not migration_succeeded or old_app_failures > 0:
        overall_severity = Severity.CRITICAL
        label = LABEL_CRITICAL_RISK
    elif (
        invariant_failures > 0
        or dropped_tables_count > 0
        or dropped_columns_count > 0
        or row_count_reduction
    ):
        overall_severity = Severity.HIGH
        label = LABEL_HIGH_RISK
    elif risky_static_count > 0 or new_app_failures > 0:
        overall_severity = Severity.MODERATE
        label = LABEL_MODERATE_RISK
    else:
        overall_severity = Severity.LOW
        label = LABEL_LOW_RISK

    # ------------------------------------------------------------------
    # Compute Secondary Heuristic Score (0-100)
    # ------------------------------------------------------------------
    raw_points = sum(f.points for f in factors)
    risk_score = min(100, max(0, raw_points))

    # Guard: Never let a low numerical score override a concrete CRITICAL finding
    if overall_severity == Severity.CRITICAL and risk_score < 30:
        risk_score = 30

    can_auto_approve = overall_severity == Severity.LOW and risk_score == 0

    return RiskAssessment(
        severity=overall_severity,
        risk_score=risk_score,
        label=label,
        reasons=tuple(reasons) if reasons else ("All configured checks completed with 0 errors.",),
        factors=tuple(factors),
        can_auto_approve=can_auto_approve,
    )


__all__ = [
    "LABEL_LOW_RISK",
    "LABEL_MODERATE_RISK",
    "LABEL_HIGH_RISK",
    "LABEL_CRITICAL_RISK",
    "RiskFactor",
    "RiskAssessment",
    "assess_risk",
]

