"""
ui/pages/overview.py
--------------------
Overview and welcome page for SchemaGuard.

Features:
  - Hero banner with official product headline and subtext.
  - Architectural overview explaining the 6-stage rehearsal pipeline.
  - 1-Click Demo Scenario Loader for instant hands-on experimentation.
  - Quick feature guide.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ui.components import info_box, render_footer, render_header, section_header, success_box

DEMO_DIR = Path("data/demo")
DEMO_DB_PATH = DEMO_DIR / "ecommerce.db"
MIGRATION_DIR = DEMO_DIR / "migrations"
CONTRACTS_DIR = DEMO_DIR / "contracts"
INVARIANTS_DIR = DEMO_DIR / "invariants"


def _read_file_safe(path: Path) -> str:
    """Read file content safely or return empty string."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_scenario(scenario_key: str) -> None:
    """Populate st.session_state with a demo scenario and route to Rehearsal."""
    st.session_state["db_source_type"] = "demo"
    st.session_state["demo_db_path"] = str(DEMO_DB_PATH.resolve())
    
    # Read contracts & invariants
    st.session_state["old_contracts_sql"] = _read_file_safe(CONTRACTS_DIR / "old_app.sql")
    st.session_state["new_contracts_sql"] = _read_file_safe(CONTRACTS_DIR / "new_app.sql")
    st.session_state["invariants_sql"] = _read_file_safe(INVARIANTS_DIR / "invariants.sql")

    if scenario_key == "safe":
        st.session_state["migration_sql"] = _read_file_safe(MIGRATION_DIR / "01_safe_add_column.sql")
        st.session_state["scenario_name"] = "Safe Column Addition (01_safe_add_column.sql)"
        st.session_state["scenario_description"] = "Adds 'phone' column to 'users' table. Both old and new application contracts pass cleanly."
    elif scenario_key == "break_contract":
        st.session_state["migration_sql"] = _read_file_safe(MIGRATION_DIR / "02_break_old_query.sql")
        st.session_state["scenario_name"] = "Breaking Contract (02_break_old_query.sql)"
        st.session_state["scenario_description"] = "Drops 'email' column from 'users'. Triggers an immediate CRITICAL failure on the existing app query contract."
    elif scenario_key == "drop_table":
        st.session_state["migration_sql"] = _read_file_safe(MIGRATION_DIR / "03_drop_table.sql")
        st.session_state["scenario_name"] = "Destructive Table Drop (03_drop_table.sql)"
        st.session_state["scenario_description"] = "Drops 'order_items' table. Triggers HIGH severity schema loss and static analysis warnings."
    
    st.session_state["demo_loaded"] = True
    st.session_state["active_page"] = "Rehearsal"
    st.rerun()


def render_overview_page() -> None:
    """Render the complete SchemaGuard overview page."""
    render_header(
        title="Know what breaks before it ships.",
        subtitle="Rehearse database migrations against an isolated copy. Verify application compatibility with evidence.",
    )

    # -----------------------------------------------------------------------
    # 1-Click Demo Scenarios (Prominently featured)
    # -----------------------------------------------------------------------
    st.markdown("#### ⚡ 1-Click Interactive Demo Scenarios")
    st.caption("Instantly test SchemaGuard using the bundled synthetic e-commerce dataset without configuring anything.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="sg-card" style="height:100%;">
                <div style="font-weight:600;font-size:0.95rem;margin-bottom:0.25rem;">🟢 Scenario 1: Safe Addition</div>
                <div style="font-size:0.82rem;color:#475569;margin-bottom:0.85rem;">
                    Rehearses <code>ALTER TABLE users ADD COLUMN phone TEXT</code>.
                    Backward compatibility remains intact.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Safe Scenario", key="btn_load_safe", use_container_width=True, type="primary"):
            load_scenario("safe")

    with col2:
        st.markdown(
            """
            <div class="sg-card" style="height:100%;">
                <div style="font-weight:600;font-size:0.95rem;margin-bottom:0.25rem;">🔴 Scenario 2: Breaking Query</div>
                <div style="font-size:0.82rem;color:#475569;margin-bottom:0.85rem;">
                    Rehearses <code>ALTER TABLE users DROP COLUMN email</code>.
                    Immediately fails <code>old_app.sql</code> contract!
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Breaking Scenario", key="btn_load_breaking", use_container_width=True):
            load_scenario("break_contract")

    with col3:
        st.markdown(
            """
            <div class="sg-card" style="height:100%;">
                <div style="font-weight:600;font-size:0.95rem;margin-bottom:0.25rem;">⚠️ Scenario 3: Drop Table</div>
                <div style="font-size:0.82rem;color:#475569;margin-bottom:0.85rem;">
                    Rehearses <code>DROP TABLE order_items</code>.
                    Triggers destructive schema warnings and diff detection.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Drop Table Scenario", key="btn_load_drop", use_container_width=True):
            load_scenario("drop_table")

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Product Explanation & Principles
    # -----------------------------------------------------------------------
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### Why Rehearse Before Deploying?")
        st.markdown(
            """
            Database migrations are high-stakes operations. A syntax-valid migration can still cause catastrophic outages if it:
            
            - **Breaks existing query contracts**: An active microservice or front-end query requests a column that was dropped or renamed.
            - **Silently violates business invariants**: A default value or constraint modification results in orphaned foreign keys or negative balances.
            - **Causes unexpected data loss**: Unintended cascades or bulk mutations reduce row counts without triggering SQL errors.

            **SchemaGuard automates pre-deployment verification** by executing proposed migrations exclusively inside an isolated temporary sandbox, replaying production query patterns, evaluating invariants, and generating an evidence-backed audit report.
            """
        )

        st.markdown("### The 6-Stage Rehearsal Pipeline")
        st.markdown(
            """
            1. **Source Inspection & Read-Only Access**: Opens your database strictly read-only (`mode=ro`). The source file is never mutated.
            2. **Sandbox Isolation**: Copies the database into a unique temporary directory via SQLite's native backup API.
            3. **Static SQL Analysis**: Parses migration AST with SQLGlot to catch unconstrained mutations and destructive DDL.
            4. **Sandboxed Migration Execution**: Applies the migration within transactional boundaries with safety authorizers (disabling ATTACH, DETACH, writable schema).
            5. **Query Contract Replay**: Replays read-only queries from both current (`OLD_APP`) and upcoming (`NEW_APP`) application releases.
            6. **Invariant Checks & Deep Diffing**: Evaluates business assertions (must return 0 rows) and computes structural schema/data profiles.
            """
        )

    with col_right:
        st.markdown("### Core Safety Guarantees")
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-weight:600;color:#0F172A;margin-bottom:0.5rem;">🔒 Zero Production Touch</div>
                <div style="font-size:0.85rem;color:#334155;line-height:1.45;">
                    The source database is opened strictly in read-only URI mode. Migrations run only on sandboxed clones.
                </div>
            </div>
            <div class="sg-card">
                <div style="font-weight:600;color:#0F172A;margin-bottom:0.5rem;">⚖️ Honest Categorical Severity</div>
                <div style="font-size:0.85rem;color:#334155;line-height:1.45;">
                    We never claim "guaranteed safe". A clean rehearsal is labeled <strong>"No configured checks failed"</strong>.
                </div>
            </div>
            <div class="sg-card">
                <div style="font-weight:600;color:#0F172A;margin-bottom:0.5rem;">⚡ Deterministic Evidence</div>
                <div style="font-size:0.85rem;color:#334155;line-height:1.45;">
                    Every finding is backed by exact SQL snippets, SQLite error messages, execution timestamps, and diff snapshots.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        info_box(
            "Ready to test your migration? Use the 1-Click Scenarios above or navigate to <strong>Rehearsal</strong> in the sidebar to upload your own database."
        )

    render_footer()
