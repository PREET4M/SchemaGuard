"""
schemaguard/core/orchestrator.py
--------------------------------
End-to-end migration rehearsal orchestration pipeline.

Sequential Pipeline:
  1. Validate source database readability and file size constraints.
  2. Inspect baseline schema and pre-migration row counts.
  3. Perform static SQL analysis with SQLGlot.
  4. Create unique temporary sandbox directory and copy DB via SQLite backup API.
  5. Execute migration exclusively against the sandbox database copy.
  6. If migration succeeds:
     - Inspect post-migration schema and data.
     - Calculate structural schema diff.
     - Profile row count changes and anomaly detections.
     - Replay OLD_APP and NEW_APP application query contracts.
     - Evaluate data invariants.
  7. If migration fails:
     - Record exact execution failure and halt post-execution checks.
  8. Calculate overall categorical severity and risk score via risk_engine.
  9. Clean up temporary sandbox connection and directory inside finally blocks.
  10. Return a typed RehearsalReport container.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from schemaguard.config import MAX_UPLOAD_SIZE_BYTES
from schemaguard.core.analyzer import analyze_migration
from schemaguard.core.contract_runner import ContractQuery, run_contracts
from schemaguard.core.data_profiler import DataProfileResult, compute_data_profile
from schemaguard.core.invariant_runner import (
    InvariantQuery,
    parse_invariants_file,
    run_invariants,
)
from schemaguard.core.migration_runner import run_migration
from schemaguard.core.risk_engine import RiskAssessment, assess_risk
from schemaguard.core.sandbox import create_sandbox
from schemaguard.core.schema_diff import diff_schemas
from schemaguard.core.schema_inspector import inspect_schema
from schemaguard.models import (
    ContractResult,
    ContractType,
    InvariantResult,
    MigrationResult,
    SchemaDiffResult,
    Severity,
)
from schemaguard.reports.json_report import export_json_report, generate_json_report
from schemaguard.reports.markdown_report import (
    export_markdown_report,
    generate_markdown_report,
)
from schemaguard.utils.file_validation import validate_sqlite_file


@dataclass(frozen=True)
class RehearsalReport:
    """Comprehensive outcome of a complete migration rehearsal run.

    Attributes:
        migration_result: Aggregated results across all verification checks.
        risk_assessment:  Calculated categorical severity and heuristic score.
        data_profile:     Table row count deltas and anomaly flags.
        post_checks_run:  True if post-migration checks were run; False if skipped on failure.
    """

    migration_result: MigrationResult
    risk_assessment: RiskAssessment
    data_profile: DataProfileResult
    post_checks_run: bool = True

    @property
    def severity(self) -> Severity:
        """Categorical risk severity (CRITICAL, HIGH, MODERATE, LOW)."""
        return self.risk_assessment.severity

    @property
    def risk_score(self) -> int:
        """Heuristic risk score between 0 and 100."""
        return self.risk_assessment.risk_score

    @property
    def label(self) -> str:
        """Human-readable verdict label."""
        return self.risk_assessment.label

    @property
    def can_auto_approve(self) -> bool:
        """True only if rehearsal passed cleanly with zero risk."""
        return self.risk_assessment.can_auto_approve

    @property
    def succeeded(self) -> bool:
        """True if migration applied and all contracts, invariants, and findings passed."""
        return self.migration_result.overall_passed()

    def to_json(self, indent: int = 2) -> str:
        """Serialize the report to formatted JSON."""
        return generate_json_report(self.migration_result, self.risk_assessment, indent=indent)

    def to_markdown(self) -> str:
        """Render the report to GitHub-flavored Markdown."""
        return generate_markdown_report(self.migration_result, self.risk_assessment)

    def export_json(self, output_path: Path | str, indent: int = 2) -> Path:
        """Write the JSON report to disk."""
        return export_json_report(
            self.migration_result, output_path, self.risk_assessment, indent=indent
        )

    def export_markdown(self, output_path: Path | str) -> Path:
        """Write the Markdown report to disk."""
        return export_markdown_report(self.migration_result, output_path, self.risk_assessment)


def _normalize_contract_items(
    items: Iterable[Any] | None,
    default_type: ContractType,
) -> list[ContractQuery]:
    """Normalize raw contract arguments into a list of ContractQuery objects."""
    if not items:
        return []

    contracts: list[ContractQuery] = []
    prefix = "old" if default_type == ContractType.OLD_APP else "new"

    for idx, item in enumerate(items):
        if isinstance(item, ContractQuery):
            contracts.append(item)
        elif isinstance(item, str):
            contracts.append(
                ContractQuery(
                    name=f"{prefix}_contract_{idx + 1}",
                    sql=item,
                    contract_type=default_type,
                )
            )
        elif isinstance(item, dict):
            c_name = item.get("name", f"{prefix}_contract_{idx + 1}")
            c_sql = item.get("sql", item.get("sql_statement", ""))
            c_type = item.get("contract_type", default_type)
            contracts.append(ContractQuery(name=c_name, sql=c_sql, contract_type=c_type))
        elif isinstance(item, (tuple, list)):
            c_name = str(item[0])
            c_sql = str(item[1])
            c_type = item[2] if len(item) > 2 else default_type
            contracts.append(ContractQuery(name=c_name, sql=c_sql, contract_type=c_type))

    return contracts


def _normalize_invariant_items(
    items: Iterable[Any] | None,
) -> list[InvariantQuery]:
    """Normalize raw invariant inputs into a list of InvariantQuery objects."""
    if not items:
        return []

    invariants: list[InvariantQuery] = []
    for idx, item in enumerate(items):
        if isinstance(item, InvariantQuery):
            invariants.append(item)
        elif isinstance(item, str):
            # Check if this string is a multi-statement file or text
            if "\n" in item or item.strip().startswith("--"):
                parsed = parse_invariants_file(item)
                if parsed:
                    invariants.extend(parsed)
                    continue
            invariants.append(InvariantQuery(name=f"invariant_{idx + 1}", sql=item))
        elif isinstance(item, dict):
            i_name = item.get("name", f"invariant_{idx + 1}")
            i_sql = item.get("sql", item.get("query", ""))
            i_desc = item.get("description", "")
            invariants.append(InvariantQuery(name=i_name, sql=i_sql, description=i_desc))
        elif isinstance(item, (tuple, list)):
            i_name = str(item[0])
            i_sql = str(item[1])
            i_desc = str(item[2]) if len(item) > 2 else ""
            invariants.append(InvariantQuery(name=i_name, sql=i_sql, description=i_desc))

    return invariants


def rehearse_migration(
    source_db_path: Path | str,
    migration_sql: str,
    *,
    old_app_contracts: Iterable[Any] | None = None,
    new_app_contracts: Iterable[Any] | None = None,
    invariants: Iterable[Any] | None = None,
    max_file_size_mb: int | None = None,
) -> RehearsalReport:
    """Run an isolated migration rehearsal pipeline and generate an evidence report.

    Args:
        source_db_path:    Filesystem path to the original SQLite database.
        migration_sql:     The complete SQL migration script.
        old_app_contracts: Queries that must remain executable post-migration.
        new_app_contracts: Queries introduced in the new application version.
        invariants:        Read-only assertions that must return zero violating rows.
        max_file_size_mb:  Upper size limit for the SQLite database.

    Returns:
        A complete, typed RehearsalReport.
    """
    overall_t0 = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Step 1: Validate source database file
    # ------------------------------------------------------------------
    size_bytes = (
        max_file_size_mb * 1024 * 1024
        if max_file_size_mb is not None
        else MAX_UPLOAD_SIZE_BYTES
    )
    resolved_source = validate_sqlite_file(source_db_path, max_size_bytes=size_bytes)

    # ------------------------------------------------------------------
    # Step 2: Inspect baseline schema & pre-migration row counts
    # ------------------------------------------------------------------
    source_uri = f"file:{resolved_source.as_posix()}?mode=ro"
    base_conn = sqlite3.connect(source_uri, uri=True)
    try:
        baseline_schema = inspect_schema(base_conn)
        baseline_row_counts = {t: schema.row_count for t, schema in baseline_schema.items()}
    finally:
        base_conn.close()

    # ------------------------------------------------------------------
    # Step 3: Static SQL analysis with SQLGlot
    # ------------------------------------------------------------------
    static_findings = tuple(analyze_migration(migration_sql))

    # ------------------------------------------------------------------
    # Step 4: Create isolated sandbox directory
    # ------------------------------------------------------------------
    sandbox = create_sandbox(resolved_source, max_size_bytes=size_bytes)

    # Ensure sandbox cleanup ALWAYS occurs
    try:
        # --------------------------------------------------------------
        # Step 5: Execute migration exclusively on sandbox copy
        # --------------------------------------------------------------
        migration_run = run_migration(sandbox, migration_sql)

        if migration_run.succeeded:
            # ----------------------------------------------------------
            # Step 6: Post-migration verification
            # ----------------------------------------------------------
            post_checks_run = True
            migration_applied = True
            migration_error = ""

            # 6a. Inspect post-migration schema
            sb_read_conn = sandbox.connect(readonly=True)
            try:
                post_schema = inspect_schema(sb_read_conn)
                post_row_counts = {t: schema.row_count for t, schema in post_schema.items()}
            finally:
                sb_read_conn.close()

            # 6b. Calculate structural schema diff & data profile
            schema_diff = diff_schemas(baseline_schema, post_schema)
            data_profile = compute_data_profile(baseline_row_counts, post_row_counts)

            # 6c. Normalize and execute query contracts
            normalized_old = _normalize_contract_items(old_app_contracts, ContractType.OLD_APP)
            normalized_new = _normalize_contract_items(new_app_contracts, ContractType.NEW_APP)
            all_contracts = normalized_old + normalized_new

            contract_results: tuple[ContractResult, ...] = (
                tuple(run_contracts(sandbox, all_contracts)) if all_contracts else ()
            )

            # 6d. Normalize and execute data invariants
            normalized_invariants = _normalize_invariant_items(invariants)
            invariant_results: tuple[InvariantResult, ...] = (
                tuple(run_invariants(sandbox, normalized_invariants))
                if normalized_invariants
                else ()
            )

        else:
            # ----------------------------------------------------------
            # Step 7: Migration failure handling (halt post-checks)
            # ----------------------------------------------------------
            post_checks_run = False
            migration_applied = False
            migration_error = migration_run.failed_error

            schema_diff = SchemaDiffResult()
            data_profile = compute_data_profile(baseline_row_counts, baseline_row_counts)
            contract_results = ()
            invariant_results = ()

        total_elapsed_ms = (time.perf_counter() - overall_t0) * 1000.0

        # Build MigrationResult aggregate
        migration_result = MigrationResult(
            source_db_path=str(resolved_source),
            sandbox_db_path=str(sandbox.sandbox_db),
            migration_sql=migration_sql,
            migration_applied=migration_applied,
            schema_diff=schema_diff,
            schema_findings=static_findings,
            contract_results=contract_results,
            invariant_results=invariant_results,
            run_timestamp_utc=timestamp_utc,
            elapsed_total_ms=round(total_elapsed_ms, 2),
            migration_error=migration_error,
        )

        # --------------------------------------------------------------
        # Step 8: Calculate overall risk assessment
        # --------------------------------------------------------------
        risk_assessment = assess_risk(migration_result)

        # --------------------------------------------------------------
        # Step 10: Return typed RehearsalReport
        # --------------------------------------------------------------
        return RehearsalReport(
            migration_result=migration_result,
            risk_assessment=risk_assessment,
            data_profile=data_profile,
            post_checks_run=post_checks_run,
        )

    finally:
        # --------------------------------------------------------------
        # Step 9: Guaranteed sandbox cleanup in finally block
        # --------------------------------------------------------------
        sandbox.cleanup()


__all__ = [
    "RehearsalReport",
    "rehearse_migration",
]

