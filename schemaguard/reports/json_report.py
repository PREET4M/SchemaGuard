"""
schemaguard/reports/json_report.py
---------------------------------
JSON evidence report exporter for SchemaGuard rehearsal runs.

Exports:
  - Execution verdict and overall risk severity
  - Secondary heuristic risk score and justifying factors
  - Static SQLGlot analysis findings
  - Application query contract re-play results
  - Data invariant evaluation results
  - Structural schema diff and row count changes

Security guarantee:
  - Strips all absolute local filesystem paths, outputting only basenames
    to protect sensitive user directory structures.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemaguard.core.risk_engine import RiskAssessment, assess_risk
from schemaguard.models import MigrationResult


def sanitize_filename(path_str: str | Path | None) -> str:
    """Return only the base filename of path_str to strip absolute local filesystem paths."""
    if not path_str:
        return ""
    return Path(path_str).name


def build_json_report_dict(
    migration_result: MigrationResult,
    risk_assessment: RiskAssessment | None = None,
) -> dict[str, Any]:
    """Construct a sanitized, serializable Python dictionary of the rehearsal run.

    Args:
        migration_result: The complete MigrationResult from the rehearsal.
        risk_assessment:  Optional pre-computed RiskAssessment.

    Returns:
        Structured dictionary ready for JSON serialization.
    """
    if risk_assessment is None:
        risk_assessment = assess_risk(migration_result)

    # 1. Database metadata
    db_meta = {
        "source_database": sanitize_filename(migration_result.source_db_path),
        "sandbox_database": sanitize_filename(migration_result.sandbox_db_path),
        "source_file": sanitize_filename(migration_result.source_db_path),
        "sandbox_file": sanitize_filename(migration_result.sandbox_db_path),
    }

    # 2. Verdict metadata
    verdict = {
        "severity": str(risk_assessment.severity.value).upper(),
        "risk_score": risk_assessment.risk_score,
        "label": risk_assessment.label,
        "can_auto_approve": risk_assessment.can_auto_approve,
        "overall_passed": migration_result.overall_passed(),
        "reasons": list(risk_assessment.reasons),
        "factors": [
            {
                "category": f.category,
                "severity": str(f.severity.value).upper(),
                "points": f.points,
                "description": f.description,
            }
            for f in risk_assessment.factors
        ],
    }

    # 3. Migration execution details
    migration_meta = {
        "applied": migration_result.migration_applied,
        "sql": migration_result.migration_sql,
        "error": migration_result.migration_error,
    }

    # 4. Static SQL findings
    static_findings = [
        {
            "rule_id": sf.rule_id,
            "severity": str(sf.severity.value).upper(),
            "title": sf.title,
            "explanation": sf.explanation,
            "evidence": sf.evidence,
            "statement_index": sf.statement_index,
            "human_review_action": sf.human_review_action,
            "is_destructive": sf.is_destructive,
        }
        for sf in migration_result.schema_findings
    ]

    # 5. Application query contracts
    contracts = [
        {
            "name": c.name,
            "contract_type": str(c.contract_type),
            "status": str(c.status),
            "sql_statement": c.sql_statement,
            "execution_time_ms": c.execution_time_ms,
            "column_names": list(c.column_names),
            "row_count_post": c.row_count_post,
            "error_message": c.error_message,
        }
        for c in migration_result.contract_results
    ]

    # 6. Data invariants
    invariants = [
        {
            "name": inv.name,
            "status": str(inv.status),
            "sql": inv.sql,
            "violating_rows_count": inv.violating_rows_count,
            "error_message": inv.error_message,
            "execution_time_ms": inv.execution_time_ms,
            "sample_violations": list(inv.sample_violations),
        }
        for inv in migration_result.invariant_results
    ]

    # 7. Structural schema diff
    diff = migration_result.schema_diff
    schema_diff_data = {
        "is_clean": diff.is_clean(),
        "has_destructive_changes": diff.has_destructive_changes(),
        "tables_added": list(diff.tables_added),
        "tables_removed": list(diff.tables_removed),
        "tables_modified": list(diff.tables_modified),
        "columns_added": {t: list(cols) for t, cols in diff.columns_added.items()},
        "columns_removed": {t: list(cols) for t, cols in diff.columns_removed.items()},
        "columns_modified": {
            t: {col: list(types) for col, types in col_map.items()}
            for t, col_map in diff.columns_modified.items()
        },
        "indexes_added": list(diff.indexes_added),
        "indexes_removed": list(diff.indexes_removed),
        "row_count_deltas": {
            t: {"pre": pair[0], "post": pair[1], "delta": pair[1] - pair[0]}
            for t, pair in diff.row_count_deltas.items()
        },
    }

    return {
        "tool": "SchemaGuard",
        "version": "0.1.0",
        "run_timestamp_utc": migration_result.run_timestamp_utc,
        "elapsed_total_ms": migration_result.elapsed_total_ms,
        "database": db_meta,
        "verdict": verdict,
        "migration": migration_meta,
        "static_findings": static_findings,
        "contracts": contracts,
        "invariants": invariants,
        "schema_diff": schema_diff_data,
    }


def generate_json_report(
    migration_result: MigrationResult,
    risk_assessment: RiskAssessment | None = None,
    indent: int = 2,
) -> str:
    """Generate a clean JSON string report for the rehearsal run."""
    report_dict = build_json_report_dict(migration_result, risk_assessment)
    return json.dumps(report_dict, indent=indent, default=str)


def export_json_report(
    migration_result: MigrationResult,
    output_path: Path | str,
    risk_assessment: RiskAssessment | None = None,
    indent: int = 2,
) -> Path:
    """Write the JSON evidence report to disk.

    Args:
        migration_result: The MigrationResult to export.
        output_path:      Target file path.
        risk_assessment:  Optional pre-computed RiskAssessment.
        indent:           JSON formatting indentation.

    Returns:
        The resolved Path of the written file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    json_text = generate_json_report(migration_result, risk_assessment, indent=indent)
    path.write_text(json_text, encoding="utf-8")
    return path


__all__ = [
    "sanitize_filename",
    "build_json_report_dict",
    "generate_json_report",
    "export_json_report",
]
