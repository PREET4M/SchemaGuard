"""
tests/test_risk_engine.py
-------------------------
Unit tests for the Risk Engine, JSON Report Exporter, and Markdown Report Generator.

Coverage:
  - Safe migration evaluates to LOW severity with label "No configured checks failed"
  - OLD_APP query contract failure evaluates to CRITICAL severity
  - Invariant failure evaluates to HIGH severity
  - Migration execution failure evaluates to CRITICAL severity (score 100)
  - Dropped table evaluates to HIGH severity (score >= 35)
  - Dropped column evaluates to HIGH severity (score >= 20)
  - NEW_APP query contract failure evaluates to MODERATE severity
  - Risky static analysis finding evaluates to MODERATE severity
  - Low numerical score never overrides a concrete CRITICAL finding
  - JSON report exports relative filenames and clean structure
  - Markdown report formats headers, sections, and disclaimer (never "guaranteed safe")
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schemaguard.core.risk_engine import (
    LABEL_CRITICAL_RISK,
    LABEL_HIGH_RISK,
    LABEL_LOW_RISK,
    LABEL_MODERATE_RISK,
    RiskAssessment,
    assess_risk,
)
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
from schemaguard.reports.json_report import (
    build_json_report_dict,
    export_json_report,
    generate_json_report,
    sanitize_filename,
)
from schemaguard.reports.markdown_report import (
    export_markdown_report,
    generate_markdown_report,
)


# ---------------------------------------------------------------------------
# Helpers & Sample Factories
# ---------------------------------------------------------------------------


def _dummy_migration_result(
    applied: bool = True,
    contract_results: tuple[ContractResult, ...] = (),
    invariant_results: tuple[InvariantResult, ...] = (),
    schema_diff: SchemaDiffResult | None = None,
    schema_findings: tuple[SchemaFinding, ...] = (),
    error: str = "",
) -> MigrationResult:
    """Create a MigrationResult fixture for reporting and risk testing."""
    return MigrationResult(
        source_db_path="D:/03_Programming/Projects/schemaguard/data/demo/ecommerce.db",
        sandbox_db_path="D:/03_Programming/Projects/schemaguard/temp_sandbox/run_123/rehearsal_copy.db",
        migration_sql="ALTER TABLE users ADD COLUMN phone TEXT;",
        migration_applied=applied,
        schema_diff=schema_diff or SchemaDiffResult(),
        schema_findings=schema_findings,
        contract_results=contract_results,
        invariant_results=invariant_results,
        run_timestamp_utc="2026-11-01T12:00:00Z",
        elapsed_total_ms=45.2,
        migration_error=error,
    )


# ===================================================================
# 1. Severity & Score Assignment Tests
# ===================================================================


class TestRiskEngineSeverities:
    """Tests for categorical severity rules and heuristic risk scoring."""

    def test_safe_migration_evaluates_to_low(self) -> None:
        """When no checks fail, severity is LOW and label is exact required string."""
        assessment = assess_risk(
            migration_succeeded=True,
            contract_results=[
                ContractResult(name="c1", status=ContractStatus.PASS, contract_type=ContractType.OLD_APP),
            ],
            invariant_results=[
                InvariantResult(name="i1", status=InvariantStatus.PASS, violating_rows_count=0),
            ],
            schema_diff=SchemaDiffResult(),
            static_findings=(),
        )

        assert assessment.severity == Severity.LOW
        assert assessment.label == "No configured checks failed"
        assert assessment.label == LABEL_LOW_RISK
        assert assessment.risk_score == 0
        assert assessment.can_auto_approve is True

    def test_migration_execution_failure_is_critical(self) -> None:
        """Failed migration execution produces CRITICAL severity and score 100."""
        assessment = assess_risk(migration_succeeded=False)

        assert assessment.severity == Severity.CRITICAL
        assert assessment.risk_score == 100
        assert assessment.can_auto_approve is False
        assert "Migration DDL execution failed" in assessment.reasons[0]

    def test_old_app_contract_failure_is_critical(self) -> None:
        """Failed OLD_APP contract produces CRITICAL severity and at least 30 points."""
        contract = ContractResult(
            name="old_app_query",
            contract_type=ContractType.OLD_APP,
            status=ContractStatus.FAIL,
            error_message="no such column: email",
        )
        assessment = assess_risk(
            migration_succeeded=True,
            contract_results=[contract],
        )

        assert assessment.severity == Severity.CRITICAL
        assert assessment.risk_score >= 30
        assert assessment.can_auto_approve is False

    def test_data_invariant_failure_is_high(self) -> None:
        """Violated data invariant produces HIGH severity."""
        inv = InvariantResult(
            name="No negative totals",
            status=InvariantStatus.FAIL,
            violating_rows_count=5,
        )
        assessment = assess_risk(
            migration_succeeded=True,
            invariant_results=[inv],
        )

        assert assessment.severity == Severity.HIGH
        assert assessment.risk_score >= 25
        assert assessment.can_auto_approve is False

    def test_dropped_table_is_high(self) -> None:
        """Dropped table in schema_diff produces HIGH severity and 35 points."""
        diff = SchemaDiffResult(tables_removed=("order_items",))
        assessment = assess_risk(
            migration_succeeded=True,
            schema_diff=diff,
        )

        assert assessment.severity == Severity.HIGH
        assert assessment.risk_score >= 35

    def test_dropped_column_is_high(self) -> None:
        """Dropped column produces HIGH severity and 20 points."""
        diff = SchemaDiffResult(columns_removed={"users": ["email"]})
        assessment = assess_risk(
            migration_succeeded=True,
            schema_diff=diff,
        )

        assert assessment.severity == Severity.HIGH
        assert assessment.risk_score >= 20

    def test_new_app_contract_failure_is_moderate(self) -> None:
        """Failed NEW_APP contract produces MODERATE severity."""
        contract = ContractResult(
            name="new_feature_query",
            contract_type=ContractType.NEW_APP,
            status=ContractStatus.FAIL,
            error_message="column missing",
        )
        assessment = assess_risk(
            migration_succeeded=True,
            contract_results=[contract],
        )

        assert assessment.severity == Severity.MODERATE
        assert assessment.risk_score >= 15

    def test_risky_static_finding_is_moderate(self) -> None:
        """Potentially risky static finding produces MODERATE severity."""
        finding = SchemaFinding(
            rule_id="SG-ST-005",
            title="ALTER TABLE rename",
            is_destructive=True,
        )
        assessment = assess_risk(
            migration_succeeded=True,
            static_findings=[finding],
        )

        assert assessment.severity == Severity.MODERATE
        assert assessment.risk_score >= 10

    def test_score_never_overrides_critical_finding(self) -> None:
        """Even if points are capped or low, CRITICAL finding retains CRITICAL severity."""
        contract = ContractResult(
            name="old_app",
            contract_type=ContractType.OLD_APP,
            status=ContractStatus.FAIL,
        )
        assessment = assess_risk(
            migration_succeeded=True,
            contract_results=[contract],
        )
        # Numerical score should be >= 30, and categorical severity strictly CRITICAL
        assert assessment.severity == Severity.CRITICAL
        assert assessment.risk_score >= 30

    def test_score_capped_at_100(self) -> None:
        """Cumulative points exceeding 100 are strictly capped at 100."""
        assessment = assess_risk(
            migration_succeeded=False,  # 100 pts
            contract_results=[
                ContractResult(name="c1", status=ContractStatus.FAIL, contract_type=ContractType.OLD_APP),  # 30 pts
            ],
            schema_diff=SchemaDiffResult(tables_removed=("t1", "t2")),  # 70 pts
        )
        assert assessment.risk_score == 100


# ===================================================================
# 2. JSON Report Tests
# ===================================================================


class TestJsonReport:
    """Tests for JSON evidence report structure and path sanitization."""

    def test_sanitize_filename_strips_absolute_paths(self) -> None:
        """Extracts only basenames and strips local filesystem details."""
        assert sanitize_filename("D:/Projects/schemaguard/db.sqlite") == "db.sqlite"
        assert sanitize_filename("C:\\Users\\Alice\\AppData\\test.db") == "test.db"
        assert sanitize_filename("") == ""

    def test_generate_json_report_structure(self) -> None:
        """Verify JSON report serializes all required sections cleanly."""
        res = _dummy_migration_result(
            applied=True,
            contract_results=(
                ContractResult(name="c1", status=ContractStatus.PASS, column_names=("id", "name")),
            ),
            invariant_results=(
                InvariantResult(name="i1", status=InvariantStatus.PASS),
            ),
        )

        json_str = generate_json_report(res)
        data = json.loads(json_str)

        assert data["tool"] == "SchemaGuard"
        assert "verdict" in data
        assert data["verdict"]["severity"] == "LOW"
        assert data["verdict"]["label"] == "No configured checks failed"
        assert data["database"]["source_file"] == "ecommerce.db"
        assert data["database"]["sandbox_file"] == "rehearsal_copy.db"

        # Verify no absolute drive paths exist in the output
        assert "D:/" not in json_str
        assert "run_123" not in json_str

    def test_export_json_report_file(self, tmp_path: Path) -> None:
        """Exporting writes a valid JSON file to disk."""
        res = _dummy_migration_result()
        out_file = tmp_path / "reports" / "report.json"

        returned_path = export_json_report(res, out_file)
        assert returned_path.is_file()
        content = json.loads(returned_path.read_text(encoding="utf-8"))
        assert content["tool"] == "SchemaGuard"


# ===================================================================
# 3. Markdown Report Tests
# ===================================================================


class TestMarkdownReport:
    """Tests for Markdown evidence report formatting and disclaimer adherence."""

    def test_generate_markdown_report_sections(self) -> None:
        """Markdown report contains expected headers and key elements."""
        res = _dummy_migration_result(
            applied=True,
            contract_results=(
                ContractResult(name="old_app", status=ContractStatus.PASS, column_names=("id",)),
            ),
            invariant_results=(
                InvariantResult(name="No negative totals", status=InvariantStatus.PASS),
            ),
            schema_diff=SchemaDiffResult(columns_added={"users": ["phone"]}),
        )

        md = generate_markdown_report(res)

        assert "# 🛡️ SchemaGuard — Migration Rehearsal Report" in md
        assert "## 1. Executive Verdict" in md
        assert "## 2. Migration Execution" in md
        assert "## 4. Application Query Contracts" in md
        assert "## 5. Data Invariants" in md
        assert "## 6. Structural Schema Diff & Row Counts" in md
        assert "No configured checks failed" in md

        # Never claim guaranteed safe
        assert "guaranteed safe" not in md.lower()
        assert "do not guarantee" in md.lower()

    def test_markdown_report_with_failures(self) -> None:
        """Markdown report highlights failed contracts and execution errors."""
        res = _dummy_migration_result(
            applied=False,
            error="syntax error near foo",
            contract_results=(
                ContractResult(
                    name="old_app_broken",
                    status=ContractStatus.FAIL,
                    error_message="column missing: email",
                ),
            ),
        )

        md = generate_markdown_report(res)
        assert "CRITICAL" in md
        assert "syntax error near foo" in md
        assert "column missing: email" in md
        assert "[!CAUTION]" in md

    def test_export_markdown_report_file(self, tmp_path: Path) -> None:
        """Exporting writes a valid Markdown file to disk."""
        res = _dummy_migration_result()
        out_file = tmp_path / "reports" / "report.md"

        returned_path = export_markdown_report(res, out_file)
        assert returned_path.is_file()
        text = returned_path.read_text(encoding="utf-8")
        assert "SchemaGuard" in text

