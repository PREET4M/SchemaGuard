"""
ui/pages/results.py
-------------------
Evidence-backed rehearsal results display page.

Presents deterministic findings:
  1. Categorical Overall Severity tag (CRITICAL, HIGH, MODERATE, LOW: "No configured checks failed").
  2. Migration execution status banner.
  3. Application query compatibility replay cards (OLD_APP & NEW_APP).
  4. Data invariants evaluation table (must return 0 rows to pass).
  5. Structural schema diff viewer (added/removed/modified tables, columns, indexes, FKs).
  6. Row-count profiler table and anomaly flags.
  7. Static SQL analysis warnings (visually separated from runtime errors).
  8. Secondary heuristic risk score breakdown with precedence note.
  9. PR-ready JSON and Markdown report export downloads.
"""

from __future__ import annotations

import streamlit as st

from schemaguard.core.orchestrator import RehearsalReport
from schemaguard.models import ContractType, Severity
from ui.components import (
    code_snippet,
    diff_badge,
    error_box,
    info_box,
    metric_tile,
    render_footer,
    render_header,
    section_header,
    severity_badge,
    status_badge,
    success_box,
    warning_box,
)


def render_results_page() -> None:
    """Render the complete migration rehearsal results page."""
    render_header(
        title="Rehearsal Evidence & Results",
        subtitle="Deterministic evidence captured during sandboxed execution.",
    )

    report: RehearsalReport | None = st.session_state.get("rehearsal_report")

    if report is None:
        st.markdown(
            """
            <div class="sg-card" style="text-align:center;padding:3rem 1.5rem;">
                <div style="font-size:2.5rem;margin-bottom:0.75rem;">📋</div>
                <div style="font-size:1.2rem;font-weight:600;color:#0F172A;margin-bottom:0.5rem;">
                    No Rehearsal Results in Context
                </div>
                <div style="font-size:0.9rem;color:#64748B;max-width:500px;margin:0 auto 1.5rem auto;">
                    Configure and execute a rehearsal on the <strong>Rehearsal</strong> page, or load an instant 1-Click scenario from the <strong>Overview</strong> page.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Go to Rehearsal Setup", use_container_width=True, type="primary"):
                st.session_state["active_page"] = "Rehearsal"
                st.rerun()
        with col2:
            if st.button("Explore 1-Click Demos", use_container_width=True):
                st.session_state["active_page"] = "Overview"
                st.rerun()
        render_footer()
        return

    # Extract report entities
    m_res = report.migration_result
    risk = report.risk_assessment
    diff = m_res.schema_diff
    findings = m_res.schema_findings
    contracts = m_res.contract_results
    invariants = m_res.invariant_results
    profile = report.data_profile

    # -----------------------------------------------------------------------
    # Top Banner: Verdict & Execution Status
    # -----------------------------------------------------------------------
    st.markdown("### Overall Verdict & Status")

    verdict_col1, verdict_col2 = st.columns([2, 1])

    with verdict_col1:
        st.markdown(
            f"""
            <div class="sg-card" style="padding:1.25rem;height:100%;">
                <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;color:#64748B;letter-spacing:0.04em;margin-bottom:0.35rem;">
                    Categorical Risk Level
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                    <span style="font-size:1.3rem;font-weight:700;">{report.severity.value.upper()}</span>
                </div>
                <div style="font-size:0.95rem;font-weight:600;color:#1E293B;margin-bottom:0.35rem;">
                    {report.label}
                </div>
                <div style="font-size:0.8rem;color:#64748B;">
                    Deterministic verdict based on contract replays, invariant evaluations, and schema modifications.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with verdict_col2:
        exec_status_text = "APPLIED SUCCESSFULLY" if m_res.migration_applied else "EXECUTION FAILED"
        exec_status_color = "#059669" if m_res.migration_applied else "#DC2626"
        exec_status_bg = "#ECFDF5" if m_res.migration_applied else "#FEF2F2"
        st.markdown(
            f"""
            <div class="sg-card" style="padding:1.25rem;height:100%;">
                <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;color:#64748B;letter-spacing:0.04em;margin-bottom:0.35rem;">
                    Sandbox Migration DDL
                </div>
                <div style="display:inline-block;padding:3px 10px;border-radius:9999px;font-size:0.8rem;font-weight:700;color:{exec_status_color};background:{exec_status_bg};margin-bottom:0.6rem;">
                    {exec_status_text}
                </div>
                <div style="font-size:0.82rem;color:#475569;">
                    Elapsed: <strong>{round(m_res.elapsed_total_ms, 1)} ms</strong><br>
                    Post-checks executed: <strong>{"Yes" if report.post_checks_run else "Halted"}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # If migration execution itself failed, show prominent error
    if not m_res.migration_applied:
        error_box(f"<strong>Migration DDL Execution Error:</strong> {m_res.migration_error}")

    # Stat summary tiles
    passed_contracts = sum(1 for c in contracts if str(c.status).upper() == "PASS")
    total_contracts = len(contracts)
    passed_inv = sum(1 for i in invariants if i.held())
    total_inv = len(invariants)
    tables_changed = len(diff.tables_added) + len(diff.tables_removed) + len(diff.tables_modified)

    stat_cols = st.columns(4)
    with stat_cols[0]:
        metric_tile("Contracts Passed", f"{passed_contracts} / {total_contracts}", "OLD_APP & NEW_APP")
    with stat_cols[1]:
        metric_tile("Invariants Held", f"{passed_inv} / {total_inv}", "0 violating rows")
    with stat_cols[2]:
        metric_tile("Tables Modified", str(tables_changed), f"+{len(diff.tables_added)} / -{len(diff.tables_removed)}")
    with stat_cols[3]:
        metric_tile("Static Warnings", str(len(findings)), "Parsed via SQLGlot")

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Secondary Heuristic Risk Score Breakdown
    # -----------------------------------------------------------------------
    with st.expander("📊 Secondary Heuristic Risk Score Breakdown", expanded=False):
        score_col1, score_col2 = st.columns([1, 2])
        with score_col1:
            st.metric("Heuristic Risk Score", f"{risk.risk_score} / 100")
            st.progress(risk.risk_score / 100)
            st.caption("Heuristic points aggregate, capped at 100.")
        with score_col2:
            if report.severity == Severity.CRITICAL:
                warning_box(
                    "⚠️ <strong>Precedence Principle:</strong> Migration execution failed or an OLD_APP "
                    "contract failed. Concrete functional failures strictly override numerical scores."
                )
            if risk.factors:
                st.markdown("**Contributing Evidence Factors:**")
                for f in risk.factors:
                    st.markdown(f"- **{f.category}** (+{f.points} pts): {f.description}")
            else:
                st.markdown("_No negative risk factors identified._")

    st.divider()

    # -----------------------------------------------------------------------
    # Application Query Contract Replays (OLD_APP & NEW_APP)
    # -----------------------------------------------------------------------
    st.markdown("### 1. Application Query Compatibility Contracts")
    st.caption("Replayed read-only against the post-migration sandbox database.")

    if not contracts:
        st.markdown("_No application contracts were configured for this rehearsal._")
    else:
        for idx, contract in enumerate(contracts):
            c_status = str(contract.status).upper()
            c_type_label = "Production Contract (OLD_APP)" if contract.contract_type == ContractType.OLD_APP else "Upcoming Contract (NEW_APP)"
            is_pass = c_status == "PASS"

            with st.container():
                st.markdown(
                    f"""
                    <div class="sg-card" style="margin-bottom:0.75rem;">
                        <div class="sg-card-header">
                            <div>
                                <span style="font-weight:600;font-size:0.95rem;color:#0F172A;">{contract.name}</span>
                                <span style="font-size:0.8rem;color:#64748B;margin-left:8px;">({c_type_label})</span>
                            </div>
                            <div>
                                <span class="sg-badge sg-badge-{'low' if is_pass else 'critical'}">{c_status}</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                code_snippet(contract.sql_statement, language="sql")

                if not is_pass:
                    error_box(f"<strong>Contract Failure:</strong> {contract.error_message}")
                else:
                    cols_desc = ", ".join(f"<code>{col}</code>" for col in contract.column_names) if contract.column_names else "_no columns returned_"
                    st.markdown(
                        f"""
                        <div style="font-size:0.85rem;color:#475569;margin-top:0.35rem;">
                            Result: <strong>{contract.row_count_post} row(s)</strong> returned in {round(contract.execution_time_ms, 2)} ms. &nbsp;|&nbsp; Columns: {cols_desc}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Data Invariants Evaluation
    # -----------------------------------------------------------------------
    st.markdown("### 2. Business Data Invariants")
    st.caption("Assertions evaluated post-migration. Invariants MUST return 0 rows to PASS.")

    if not invariants:
        st.markdown("_No data invariants were configured for this rehearsal._")
    else:
        for idx, inv in enumerate(invariants):
            inv_pass = inv.held()
            status_text = "PASS" if inv_pass else ("FAIL" if inv.status == "FAIL" else "ERROR")
            badge_class = "low" if inv_pass else "critical"

            st.markdown(
                f"""
                <div class="sg-card" style="margin-bottom:0.75rem;">
                    <div class="sg-card-header">
                        <div>
                            <span style="font-weight:600;font-size:0.95rem;color:#0F172A;">{inv.name}</span>
                        </div>
                        <div>
                            <span class="sg-badge sg-badge-{badge_class}">{status_text}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            code_snippet(inv.sql, language="sql")

            if inv_pass:
                st.markdown(
                    f"<div style='font-size:0.85rem;color:#059669;'>✓ Invariant held: <strong>0 violating rows</strong> found ({round(inv.execution_time_ms, 2)} ms).</div>",
                    unsafe_allow_html=True,
                )
            else:
                if inv.error_message:
                    error_box(f"<strong>Invariant Evaluation Error:</strong> {inv.error_message}")
                else:
                    error_box(f"<strong>Invariant Violated:</strong> Returned <strong>{inv.violating_rows_count} violating row(s)</strong>!")
                    if inv.sample_violations:
                        with st.expander(f"View Sample Violating Rows ({len(inv.sample_violations)} samples)"):
                            st.table(list(inv.sample_violations))

            st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Structural Schema Diff
    # -----------------------------------------------------------------------
    st.markdown("### 3. Structural Schema Diff")
    st.caption("Comparison between baseline pre-migration schema and post-migration sandbox schema.")

    if diff.is_clean():
        st.markdown("_No structural schema changes detected._")
    else:
        diff_col1, diff_col2 = st.columns(2)

        with diff_col1:
            st.markdown("#### Table Changes")
            if diff.tables_added:
                for t in diff.tables_added:
                    st.markdown(f"- {diff_badge('ADDED')} Table `<strong>{t}</strong>`", unsafe_allow_html=True)
            if diff.tables_removed:
                for t in diff.tables_removed:
                    st.markdown(f"- {diff_badge('REMOVED')} Table `<strong>{t}</strong>`", unsafe_allow_html=True)
            if not diff.tables_added and not diff.tables_removed:
                st.markdown("_No tables added or dropped._")

            st.markdown("#### Index & Constraint Changes")
            if diff.indexes_added:
                for idx_name in diff.indexes_added:
                    st.markdown(f"- {diff_badge('ADDED')} Index `{idx_name}`", unsafe_allow_html=True)
            if diff.indexes_removed:
                for idx_name in diff.indexes_removed:
                    st.markdown(f"- {diff_badge('REMOVED')} Index `{idx_name}`", unsafe_allow_html=True)
            if diff.foreign_keys_added:
                for tbl, fks in diff.foreign_keys_added.items():
                    for fk in fks:
                        st.markdown(f"- {diff_badge('ADDED')} FK on `{tbl}`: `{fk}`", unsafe_allow_html=True)
            if diff.foreign_keys_removed:
                for tbl, fks in diff.foreign_keys_removed.items():
                    for fk in fks:
                        st.markdown(f"- {diff_badge('REMOVED')} FK on `{tbl}`: `{fk}`", unsafe_allow_html=True)

        with diff_col2:
            st.markdown("#### Column Changes")
            if diff.columns_added:
                for tbl, cols in diff.columns_added.items():
                    for col in cols:
                        st.markdown(f"- {diff_badge('ADDED')} Column `<strong>{tbl}.{col}</strong>`", unsafe_allow_html=True)
            if diff.columns_removed:
                for tbl, cols in diff.columns_removed.items():
                    for col in cols:
                        st.markdown(f"- {diff_badge('REMOVED')} Column `<strong>{tbl}.{col}</strong>`", unsafe_allow_html=True)
            if diff.columns_modified:
                for tbl, col_dict in diff.columns_modified.items():
                    for col, (old_t, new_t) in col_dict.items():
                        st.markdown(f"- {diff_badge('MODIFIED')} Column `<strong>{tbl}.{col}</strong>` type changed: `{old_t}` → `{new_t}`", unsafe_allow_html=True)
            if not diff.columns_added and not diff.columns_removed and not diff.columns_modified:
                st.markdown("_No column changes detected._")

    st.divider()

    # -----------------------------------------------------------------------
    # Row-Count Profiler Table
    # -----------------------------------------------------------------------
    st.markdown("### 4. Data Row-Count Profiler")
    st.caption("Tracking table row counts across rehearsal boundaries to catch unexpected data losses.")

    if profile and profile.table_deltas:
        profile_rows = []
        for tp in profile.table_deltas.values():
            if tp.delta is not None:
                delta_str = f"+{tp.delta}" if tp.delta > 0 else str(tp.delta)
            else:
                delta_str = "N/A"

            if tp.pre_count and tp.pre_count > 0 and tp.delta is not None:
                pct_str = f"{(tp.delta / tp.pre_count) * 100:+.1f}%"
            elif tp.status == "created":
                pct_str = "NEW"
            elif tp.status == "dropped":
                pct_str = "DROPPED"
            else:
                pct_str = "0.0%"

            anomaly_icon = "⚠️ DROP" if (tp.is_row_drop or tp.status == "dropped") else "✓"
            profile_rows.append({
                "Table": tp.table_name,
                "Pre-Migration Rows": tp.pre_count if tp.pre_count is not None else 0,
                "Post-Migration Rows": tp.post_count if tp.post_count is not None else 0,
                "Delta": delta_str,
                "Change (%)": pct_str,
                "Status": anomaly_icon,
            })
        st.dataframe(profile_rows, use_container_width=True)
    else:
        st.markdown("_No table row count profiles available._")

    st.divider()

    # -----------------------------------------------------------------------
    # Static SQL Analysis Warnings (Visually separated from runtime errors)
    # -----------------------------------------------------------------------
    st.markdown("### 5. Static SQL Analysis Warnings")
    st.caption("Identified by AST inspection with SQLGlot before execution. Visually separated from runtime errors.")

    if not findings:
        success_box("✓ No static SQL warnings detected. No unconstrained bulk deletes or dropped objects found in AST.")
    else:
        for f in findings:
            f_sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            badge_kind = "critical" if f_sev in ("critical", "high") else ("moderate" if f_sev in ("moderate", "warning") else "info")
            st.markdown(
                f"""
                <div class="sg-card" style="margin-bottom:0.75rem;">
                    <div class="sg-card-header">
                        <div>
                            <span class="sg-badge sg-badge-{badge_kind}">{f_sev.upper()}</span>
                            <span style="font-weight:600;font-size:0.95rem;color:#0F172A;margin-left:8px;">{f.title or f.rule_id}</span>
                            <span style="font-size:0.8rem;color:#64748B;margin-left:6px;">[{f.rule_id}]</span>
                        </div>
                    </div>
                    <div style="font-size:0.88rem;color:#334155;margin-bottom:0.5rem;">
                        {f.explanation}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if f.evidence:
                code_snippet(f.evidence, language="sql")
            if f.human_review_action:
                st.markdown(f"<div style='font-size:0.82rem;color:#0284C7;margin-bottom:0.75rem;'>👉 <strong>Recommended Review:</strong> {f.human_review_action}</div>", unsafe_allow_html=True)

    st.divider()

    # -----------------------------------------------------------------------
    # Export Evidence Reports
    # -----------------------------------------------------------------------
    st.markdown("### 6. Evidence Report Export")
    st.caption("Download deterministic reports ready for pull request review and compliance.")

    col_dl1, col_dl2, col_actions = st.columns([1, 1, 2])

    json_str = report.to_json(indent=2)
    md_str = report.to_markdown()

    with col_dl1:
        st.download_button(
            label="📥 Download JSON Report",
            data=json_str,
            file_name="schemaguard_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with col_dl2:
        st.download_button(
            label="📄 Download Markdown Report",
            data=md_str,
            file_name="schemaguard_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col_actions:
        if st.button("🔄 Configure New Rehearsal", use_container_width=True):
            st.session_state["active_page"] = "Rehearsal"
            st.rerun()

    render_footer()
