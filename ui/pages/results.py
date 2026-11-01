"""
ui/pages/results.py
-------------------
Evidence-backed rehearsal results display — high-impact analysis studio.

Presents deterministic findings:
  1. Categorical Overall Severity tag (CRITICAL, HIGH, MODERATE, LOW: "No configured checks failed").
  2. Migration execution status banner.
  3. Side-by-side metric comparison tiles.
  4. Interactive result tabs: Application Contracts, Invariants, Schema Diff, Row Profiler, Static Warnings.
  5. Secondary heuristic risk score breakdown with precedence principle warning.
  6. PR-ready JSON and Markdown report export downloads.
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
    """Render the Apple / Linear inspired migration rehearsal results page."""
    render_header(
        title="Rehearsal Evidence & Results",
        subtitle="Deterministic evidence captured during sandboxed execution.",
        badge_text="AUDIT READY",
    )

    report: RehearsalReport | None = st.session_state.get("rehearsal_report")

    if report is None:
        st.markdown(
            """
            <div class="sg-card" style="text-align:center;padding:3.5rem 1.5rem;max-width:640px;margin:2rem auto;">
                <div style="font-size:3rem;margin-bottom:1rem;">📋</div>
                <div style="font-size:1.35rem;font-weight:700;color:#F8FAFC;margin-bottom:0.5rem;letter-spacing:-0.02em;">
                    No Active Rehearsal Results
                </div>
                <div style="font-size:0.92rem;color:#94A3B8;line-height:1.5;margin-bottom:2rem;">
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
    # Top Status Header: Verdict & Execution Metadata
    # -----------------------------------------------------------------------
    verdict_col1, verdict_col2 = st.columns([2, 1])

    sev_str = report.severity.value.lower()
    if sev_str == "critical":
        sev_color = "#EF4444"
        sev_bg = "rgba(239, 68, 68, 0.12)"
        sev_border = "rgba(239, 68, 68, 0.35)"
    elif sev_str == "high":
        sev_color = "#F97316"
        sev_bg = "rgba(249, 115, 22, 0.12)"
        sev_border = "rgba(249, 115, 22, 0.35)"
    elif sev_str in ("moderate", "warning"):
        sev_color = "#EAB308"
        sev_bg = "rgba(234, 179, 8, 0.12)"
        sev_border = "rgba(234, 179, 8, 0.35)"
    else:
        sev_color = "#22C55E"
        sev_bg = "rgba(34, 197, 94, 0.12)"
        sev_border = "rgba(34, 197, 94, 0.35)"

    with verdict_col1:
        st.markdown(
            f"""
            <div class="sg-card" style="padding:1.5rem;height:100%;border-left:4px solid {sev_color};">
                <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;color:#94A3B8;letter-spacing:0.06em;margin-bottom:0.4rem;">
                    Categorical Risk Level
                </div>
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                    <span style="font-size:1.6rem;font-weight:800;color:{sev_color};letter-spacing:-0.02em;">
                        {report.severity.value.upper()}
                    </span>
                    <span style="background:{sev_bg};color:{sev_color};border:1px solid {sev_border};padding:2px 10px;border-radius:9999px;font-size:11px;font-weight:700;">
                        {report.label}
                    </span>
                </div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;">
                    Deterministic verdict based on application contract replays, domain invariant assertions, and structural schema modifications.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with verdict_col2:
        exec_status_text = "APPLIED SUCCESSFULLY" if m_res.migration_applied else "EXECUTION FAILED"
        exec_status_color = "#22C55E" if m_res.migration_applied else "#EF4444"
        exec_status_bg = "rgba(34, 197, 94, 0.12)" if m_res.migration_applied else "rgba(239, 68, 68, 0.12)"
        exec_status_border = "rgba(34, 197, 94, 0.3)" if m_res.migration_applied else "rgba(239, 68, 68, 0.3)"

        st.markdown(
            f"""
            <div class="sg-card" style="padding:1.5rem;height:100%;">
                <div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;color:#94A3B8;letter-spacing:0.06em;margin-bottom:0.4rem;">
                    Sandboxed Migration DDL
                </div>
                <div style="display:inline-block;padding:3px 12px;border-radius:9999px;font-size:0.8rem;font-weight:700;color:{exec_status_color};background:{exec_status_bg};border:1px solid {exec_status_border};margin-bottom:0.6rem;">
                    {exec_status_text}
                </div>
                <div style="font-size:0.82rem;color:#94A3B8;line-height:1.5;">
                    Total Elapsed: <strong style="color:#F8FAFC;">{round(m_res.elapsed_total_ms, 1)} ms</strong><br>
                    Post-checks executed: <strong style="color:#F8FAFC;">{"Yes" if report.post_checks_run else "Halted"}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # If migration execution itself failed, show prominent error
    if not m_res.migration_applied:
        error_box(f"<strong>Migration DDL Execution Error:</strong> {m_res.migration_error}")

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Summary Metrics Comparison
    # -----------------------------------------------------------------------
    passed_contracts = sum(1 for c in contracts if str(c.status).upper() == "PASS")
    total_contracts = len(contracts)
    passed_inv = sum(1 for i in invariants if i.held())
    total_inv = len(invariants)
    tables_changed = len(diff.tables_added) + len(diff.tables_removed) + len(diff.tables_modified)

    stat_cols = st.columns(4)
    with stat_cols[0]:
        metric_tile("Contracts Replayed", f"{passed_contracts} / {total_contracts}", "OLD_APP & NEW_APP")
    with stat_cols[1]:
        metric_tile("Invariants Held", f"{passed_inv} / {total_inv}", "0 violating rows required")
    with stat_cols[2]:
        metric_tile("Tables Altered", str(tables_changed), f"+{len(diff.tables_added)} / -{len(diff.tables_removed)}")
    with stat_cols[3]:
        metric_tile("Static Warnings", str(len(findings)), "Parsed via SQLGlot AST")

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Secondary Heuristic Risk Score Breakdown
    # -----------------------------------------------------------------------
    with st.expander("📊 Secondary Heuristic Risk Score Breakdown", expanded=False):
        score_col1, score_col2 = st.columns([1, 2])
        with score_col1:
            st.metric("Heuristic Risk Score", f"{risk.risk_score} / 100")
            st.progress(risk.risk_score / 100)
            st.caption("Points aggregate across all findings (0-100).")
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

    st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin:1.75rem 0;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Interactive Result Tabs (Linear / Apple Grade)
    # -----------------------------------------------------------------------
    tab_contracts, tab_invs, tab_diff, tab_prof, tab_warnings = st.tabs([
        f"Application Contracts ({total_contracts})",
        f"Business Invariants ({total_inv})",
        f"Schema Diff ({tables_changed})",
        "Row Profiler",
        f"Static Warnings ({len(findings)})",
    ])

    # --- TAB 1: APPLICATION CONTRACTS ---
    with tab_contracts:
        st.markdown(
            "<div style='font-size:0.9rem;color:#94A3B8;margin-bottom:1rem;'>"
            "Replayed read-only queries from both production (OLD_APP) and upcoming (NEW_APP) releases.</div>",
            unsafe_allow_html=True,
        )

        if not contracts:
            st.markdown("_No application contracts were configured for this rehearsal._")
        else:
            for idx, contract in enumerate(contracts):
                c_status = str(contract.status).upper()
                c_type_label = (
                    "Production Contract (OLD_APP)"
                    if contract.contract_type == ContractType.OLD_APP
                    else "Upcoming Contract (NEW_APP)"
                )
                is_pass = c_status == "PASS"

                st.markdown(
                    f"""
                    <div class="sg-card" style="margin-bottom:0.85rem;">
                        <div class="sg-card-header">
                            <div>
                                <span style="font-weight:700;font-size:1rem;color:#F8FAFC;">{contract.name}</span>
                                <span style="font-size:0.8rem;color:#94A3B8;margin-left:8px;">({c_type_label})</span>
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
                    cols_desc = (
                        ", ".join(f"<code>{col}</code>" for col in contract.column_names)
                        if contract.column_names
                        else "_no columns returned_"
                    )
                    st.markdown(
                        f"""
                        <div style="font-size:0.85rem;color:#94A3B8;margin-top:0.35rem;">
                            Result: <strong style="color:#F8FAFC;">{contract.row_count_post} row(s)</strong> returned in {round(contract.execution_time_ms, 2)} ms. &nbsp;|&nbsp; Columns: {cols_desc}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='margin-bottom:1.25rem;'></div>", unsafe_allow_html=True)

    # --- TAB 2: DATA INVARIANTS ---
    with tab_invs:
        st.markdown(
            "<div style='font-size:0.9rem;color:#94A3B8;margin-bottom:1rem;'>"
            "Assertions evaluated post-migration. Invariants MUST return 0 rows to PASS.</div>",
            unsafe_allow_html=True,
        )

        if not invariants:
            st.markdown("_No data invariants were configured for this rehearsal._")
        else:
            for idx, inv in enumerate(invariants):
                inv_pass = inv.held()
                status_text = "PASS" if inv_pass else ("FAIL" if inv.status == "FAIL" else "ERROR")
                badge_class = "low" if inv_pass else "critical"

                st.markdown(
                    f"""
                    <div class="sg-card" style="margin-bottom:0.85rem;">
                        <div class="sg-card-header">
                            <div>
                                <span style="font-weight:700;font-size:1rem;color:#F8FAFC;">{inv.name}</span>
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
                        f"<div style='font-size:0.85rem;color:#22C55E;font-weight:600;'>✓ Invariant held: <strong>0 violating rows</strong> found ({round(inv.execution_time_ms, 2)} ms).</div>",
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

                st.markdown("<div style='margin-bottom:1.25rem;'></div>", unsafe_allow_html=True)

    # --- TAB 3: SCHEMA DIFF ---
    with tab_diff:
        st.markdown(
            "<div style='font-size:0.9rem;color:#94A3B8;margin-bottom:1rem;'>"
            "Structural schema diff between baseline pre-migration and post-migration sandbox database.</div>",
            unsafe_allow_html=True,
        )

        if diff.is_clean():
            st.markdown("_No structural schema changes detected._")
        else:
            diff_col1, diff_col2 = st.columns(2)

            with diff_col1:
                st.markdown("#### Table & Constraint Changes")
                if diff.tables_added:
                    for t in diff.tables_added:
                        st.markdown(f"- {diff_badge('ADDED')} Table `<strong>{t}</strong>`", unsafe_allow_html=True)
                if diff.tables_removed:
                    for t in diff.tables_removed:
                        st.markdown(f"- {diff_badge('REMOVED')} Table `<strong>{t}</strong>`", unsafe_allow_html=True)
                if not diff.tables_added and not diff.tables_removed:
                    st.markdown("_No tables added or dropped._")

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
                            st.markdown(f"- {diff_badge('MODIFIED')} Column `<strong>{tbl}.{col}</strong>` type: `{old_t}` → `{new_t}`", unsafe_allow_html=True)
                if not diff.columns_added and not diff.columns_removed and not diff.columns_modified:
                    st.markdown("_No column changes detected._")

    # --- TAB 4: ROW PROFILER ---
    with tab_prof:
        st.markdown(
            "<div style='font-size:0.9rem;color:#94A3B8;margin-bottom:1rem;'>"
            "Table row-count metrics across rehearsal boundaries to detect unintended data drop anomalies.</div>",
            unsafe_allow_html=True,
        )

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

    # --- TAB 5: STATIC SQL WARNINGS ---
    with tab_warnings:
        st.markdown(
            "<div style='font-size:0.9rem;color:#94A3B8;margin-bottom:1rem;'>"
            "Identified by AST inspection with SQLGlot before execution. Visually separated from runtime errors.</div>",
            unsafe_allow_html=True,
        )

        if not findings:
            success_box("✓ No static SQL warnings detected. No unconstrained bulk deletes or dropped objects found in AST.")
        else:
            for f in findings:
                f_sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                badge_kind = (
                    "critical"
                    if f_sev in ("critical", "high")
                    else ("moderate" if f_sev in ("moderate", "warning") else "info")
                )
                st.markdown(
                    f"""
                    <div class="sg-card" style="margin-bottom:0.85rem;">
                        <div class="sg-card-header">
                            <div>
                                <span class="sg-badge sg-badge-{badge_kind}">{f_sev.upper()}</span>
                                <span style="font-weight:700;font-size:0.95rem;color:#F8FAFC;margin-left:8px;">{f.title or f.rule_id}</span>
                                <span style="font-size:0.8rem;color:#94A3B8;margin-left:6px;">[{f.rule_id}]</span>
                            </div>
                        </div>
                        <div style="font-size:0.88rem;color:#CBD5E1;margin-bottom:0.5rem;">
                            {f.explanation}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if f.evidence:
                    code_snippet(f.evidence, language="sql")
                if f.human_review_action:
                    st.markdown(
                        f"<div style='font-size:0.82rem;color:#06B6D4;margin-bottom:0.75rem;'>👉 <strong>Recommended Review:</strong> {f.human_review_action}</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin:2.5rem 0;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Evidence Export Action Bar
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.25rem;">
            Evidence Report Export
        </div>
        <div style="font-size:0.85rem;color:#94A3B8;margin-bottom:1rem;">
            Download deterministic evidence packages ready for pull request reviews and compliance audits.
        </div>
        """,
        unsafe_allow_html=True,
    )

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
