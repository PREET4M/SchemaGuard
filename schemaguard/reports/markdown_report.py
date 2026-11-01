"""
schemaguard/reports/markdown_report.py
-------------------------------------
Deterministic Markdown report generator for SchemaGuard migration rehearsals.

Presents evidence-backed verification summaries suitable for PR attachments,
review discussions, and CI/CD audit logs.

Strict Policy:
  Never claims guaranteed safety; clearly highlights test coverage boundaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from schemaguard.core.risk_engine import RiskAssessment, assess_risk
from schemaguard.models import ContractStatus, InvariantStatus, MigrationResult, Severity
from schemaguard.reports.json_report import sanitize_filename

_DISCLAIMER_TEXT: Final[str] = (
    "> [!WARNING]\n"
    "> **Rehearsal Scope & Disclaimer:** SchemaGuard evaluates migration compatibility "
    "against provided read-only query contracts and data invariants in an isolated sandbox. "
    "Passing checks indicate that verified contracts and invariants held; they **do not guarantee** "
    "runtime safety or complete absence of edge-case bugs in production."
)


def generate_markdown_report(
    migration_result: MigrationResult,
    risk_assessment: RiskAssessment | None = None,
) -> str:
    """Generate a GitHub-flavored Markdown evidence report for a rehearsal run.

    Args:
        migration_result: Complete MigrationResult from the rehearsal.
        risk_assessment:  Optional pre-computed RiskAssessment.

    Returns:
        Formatted Markdown report string.
    """
    if risk_assessment is None:
        risk_assessment = assess_risk(migration_result)

    db_name = sanitize_filename(migration_result.source_db_path) or "database.db"
    sev_str = str(risk_assessment.severity.value).upper()

    badge_emoji = {
        Severity.CRITICAL: "🚨",
        Severity.HIGH: "⚠️",
        Severity.MODERATE: "🟡",
        Severity.LOW: "✅",
    }.get(risk_assessment.severity, "ℹ️")

    lines: list[str] = [
        "# 🛡️ SchemaGuard — Migration Rehearsal Report",
        "",
        f"**Database:** `{db_name}`  ",
        f"**Timestamp:** `{migration_result.run_timestamp_utc or 'N/A'}`  ",
        f"**Total Rehearsal Time:** `{migration_result.elapsed_total_ms:.2f} ms`",
        "",
        "---",
        "",
        "## 1. Executive Verdict",
        "",
        f"### {badge_emoji} Risk Level: **{sev_str}** (Score: `{risk_assessment.risk_score} / 100`)",
        f"**Verdict:** {risk_assessment.label}",
        "",
    ]

    # Justification list
    if risk_assessment.reasons:
        lines.append("**Key Findings & Justifications:**")
        for reason in risk_assessment.reasons:
            lines.append(f"- {reason}")
        lines.append("")

    # Auto-approval signal
    if risk_assessment.can_auto_approve:
        lines.append("> [!NOTE]\n> Rehearsal passed with zero detected regressions across all configured checks.")
    else:
        lines.append(f"> [!CAUTION]\n> Human review required before production deployment ({sev_str} severity).")
    lines.append("")

    # ------------------------------------------------------------------
    # 2. Migration Execution
    # ------------------------------------------------------------------
    lines.extend([
        "## 2. Migration Execution",
        "",
        f"- **Migration Applied:** `{'YES' if migration_result.migration_applied else 'NO'}`",
    ])
    if migration_result.migration_error:
        lines.extend([
            f"- **Execution Error:** `{migration_result.migration_error}`",
            "",
            "> [!CAUTION]",
            f"> Migration failed during sandbox execution: `{migration_result.migration_error}`",
        ])
    lines.extend([
        "",
        "<details>",
        "<summary>View Rehearsed SQL Migration</summary>",
        "",
        "```sql",
        migration_result.migration_sql.strip(),
        "```",
        "</details>",
        "",
    ])

    # ------------------------------------------------------------------
    # 3. Static Analysis Findings
    # ------------------------------------------------------------------
    lines.append("## 3. Static SQL Analysis")
    if not migration_result.schema_findings:
        lines.append("No static code warnings detected.")
    else:
        lines.extend([
            "| Rule ID | Severity | Title | Statement Index | Human Review Action |",
            "|---|---|---|:---:|---|",
        ])
        for sf in migration_result.schema_findings:
            sev_badge = str(sf.severity.value).upper()
            lines.append(
                f"| `{sf.rule_id}` | `{sev_badge}` | {sf.title} | {sf.statement_index} | {sf.human_review_action} |"
            )
    lines.append("")

    # ------------------------------------------------------------------
    # 4. Application Query Contracts
    # ------------------------------------------------------------------
    lines.append("## 4. Application Query Contracts")
    if not migration_result.contract_results:
        lines.append("No query contracts were configured for this run.")
    else:
        lines.extend([
            "| Contract Name | Type | Status | Time (ms) | Returned Columns | Details |",
            "|---|---|:---:|:---:|---|---|",
        ])
        for c in migration_result.contract_results:
            status_icon = "✅ PASS" if c.status == ContractStatus.PASS else f"❌ {c.status}"
            cols = ", ".join(f"`{col}`" for col in c.column_names) if c.column_names else "-"
            err = c.error_message if c.error_message else "OK"
            lines.append(
                f"| `{c.name}` | `{c.contract_type}` | {status_icon} | {c.execution_time_ms:.1f} | {cols} | {err} |"
            )
    lines.append("")

    # ------------------------------------------------------------------
    # 5. Data Invariants
    # ------------------------------------------------------------------
    lines.append("## 5. Data Invariants")
    if not migration_result.invariant_results:
        lines.append("No data invariants were configured for this run.")
    else:
        lines.extend([
            "| Invariant Name | Status | Violations Count | Details |",
            "|---|:---:|:---:|---|",
        ])
        for inv in migration_result.invariant_results:
            inv_icon = "✅ PASS" if inv.status == InvariantStatus.PASS else f"❌ {inv.status}"
            details = inv.error_message if inv.error_message else "0 violating rows"
            lines.append(
                f"| `{inv.name}` | {inv_icon} | {inv.violating_rows_count} | {details} |"
            )
    lines.append("")

    # ------------------------------------------------------------------
    # 6. Schema Changes & Row Counts
    # ------------------------------------------------------------------
    diff = migration_result.schema_diff
    lines.extend([
        "## 6. Structural Schema Diff & Row Counts",
        "",
        f"- **Tables Added:** {', '.join(f'`{t}`' for t in diff.tables_added) if diff.tables_added else 'None'}",
        f"- **Tables Dropped:** {', '.join(f'`{t}`' for t in diff.tables_removed) if diff.tables_removed else 'None'}",
        f"- **Tables Modified:** {', '.join(f'`{t}`' for t in diff.tables_modified) if diff.tables_modified else 'None'}",
    ])

    if diff.columns_added:
        for t, cols in diff.columns_added.items():
            lines.append(f"  - Added to `{t}`: {', '.join(f'`{c}`' for c in cols)}")

    if diff.columns_removed:
        for t, cols in diff.columns_removed.items():
            lines.append(f"  - Dropped from `{t}`: {', '.join(f'`{c}`' for c in cols)}")

    if diff.columns_modified:
        for t, col_map in diff.columns_modified.items():
            for c, (old_t, new_t) in col_map.items():
                lines.append(f"  - Altered in `{t}`: `{c}` (`{old_t}` → `{new_t}`)")

    if diff.row_count_deltas:
        lines.extend([
            "",
            "### Table Row Count Tracking",
            "",
            "| Table | Baseline Rows | Post-Migration Rows | Net Delta |",
            "|---|:---:|:---:|:---:|",
        ])
        for t, (pre, post) in diff.row_count_deltas.items():
            delta = post - pre
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            lines.append(f"| `{t}` | {pre} | {post} | {delta_str} |")
    lines.append("")

    # ------------------------------------------------------------------
    # 7. Recommendations & Disclaimer
    # ------------------------------------------------------------------
    lines.extend([
        "## 7. Review Recommendations",
        "",
        "1. Check all failed contracts and review whether queries need updates.",
        "2. Ensure dropped columns/tables are genuinely obsolete.",
        "3. Review foreign keys and ensure no orphaned dependencies.",
        "",
        _DISCLAIMER_TEXT,
        "",
    ])

    return "\n".join(lines)


def export_markdown_report(
    migration_result: MigrationResult,
    output_path: Path | str,
    risk_assessment: RiskAssessment | None = None,
) -> Path:
    """Write the Markdown evidence report to disk."""
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    md_text = generate_markdown_report(migration_result, risk_assessment)
    path.write_text(md_text, encoding="utf-8")
    return path


__all__ = [
    "generate_markdown_report",
    "export_markdown_report",
]

