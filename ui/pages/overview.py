"""
ui/pages/overview.py
--------------------
Overview and welcome page for SchemaGuard.

Features:
  - Apple-grade editorial hero banner with dynamic typography.
  - 1-Click interactive demo scenario cards with hover elevation and metadata badges.
  - High-density capability metric tiles.
  - The 6-stage isolated rehearsal workflow architecture.
  - Core safety principles and guarantees.
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ui.components import (
    diff_badge,
    info_box,
    metric_tile,
    render_footer,
    render_header,
    section_header,
    success_box,
)

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
    """Render the Apple / Linear inspired SchemaGuard overview page."""
    render_header(
        title="Know what breaks before it ships.",
        subtitle="Validate schema migrations against real application contracts before they reach production. Completely isolated. Deterministic. Evidence-backed.",
        badge_text="✦ VERSION 2.0 • LOCAL-FIRST REHEARSAL ENGINE",
    )

    # -----------------------------------------------------------------------
    # System Capability Metric Row
    # -----------------------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_tile("Sandbox Isolation", "100%", "Native SQLite Backup API", delta="SECURE")
    with m2:
        metric_tile("Production Touch", "0 Writes", "Source opened with mode=ro", delta="SAFE")
    with m3:
        metric_tile("Contract Engine", "Dual-Replay", "OLD_APP & NEW_APP validated")
    with m4:
        metric_tile("Static Parser", "SQLGlot AST", "Pre-execution risk detection")

    st.markdown("<div style='margin-top:2.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # 1-Click Interactive Demo Scenarios
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:1rem;">
            <div>
                <span style="font-size:1.35rem;font-weight:700;color:#F8FAFC;letter-spacing:-0.02em;">Interactive Scenarios</span>
                <span style="font-size:0.9rem;color:#94A3B8;margin-left:8px;">1-click live experiments using synthetic ecommerce.db</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="sg-card sg-card-interactive" style="height:230px;display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
                        <span class="sg-badge sg-badge-low">PASSING BASELINE</span>
                        <span style="font-size:0.75rem;color:#64748B;font-family:monospace;">01_safe</span>
                    </div>
                    <div style="font-weight:700;font-size:1.05rem;color:#F8FAFC;margin-bottom:0.4rem;">
                        Safe Column Addition
                    </div>
                    <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:0.75rem;">
                        Appends <code>phone TEXT</code> to <code>users</code>. Replays verify existing queries continue executing without interruption.
                    </div>
                </div>
                <div style="font-size:0.75rem;color:#22C55E;font-weight:600;display:flex;gap:6px;">
                    <span>+1 Column</span> • <span>0 Invariant Breaches</span>
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
            <div class="sg-card sg-card-interactive" style="height:230px;display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
                        <span class="sg-badge sg-badge-critical">CRITICAL BREAK</span>
                        <span style="font-size:0.75rem;color:#64748B;font-family:monospace;">02_break</span>
                    </div>
                    <div style="font-weight:700;font-size:1.05rem;color:#F8FAFC;margin-bottom:0.4rem;">
                        Breaking Query Contract
                    </div>
                    <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:0.75rem;">
                        Drops <code>email</code> from <code>users</code>. Triggers an immediate CRITICAL failure on the active application query contract.
                    </div>
                </div>
                <div style="font-size:0.75rem;color:#EF4444;font-weight:600;display:flex;gap:6px;">
                    <span>-1 Column</span> • <span>OLD_APP Contract Broken</span>
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
            <div class="sg-card sg-card-interactive" style="height:230px;display:flex;flex-direction:column;justify-content:space-between;">
                <div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;">
                        <span class="sg-badge sg-badge-high">HIGH RISK</span>
                        <span style="font-size:0.75rem;color:#64748B;font-family:monospace;">03_drop</span>
                    </div>
                    <div style="font-weight:700;font-size:1.05rem;color:#F8FAFC;margin-bottom:0.4rem;">
                        Destructive Table Drop
                    </div>
                    <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:0.75rem;">
                        Executes <code>DROP TABLE order_items</code>. Triggers AST static warnings and schema removal alerts.
                    </div>
                </div>
                <div style="font-size:0.75rem;color:#F97316;font-weight:600;display:flex;gap:6px;">
                    <span>-1 Table</span> • <span>Destructive DDL Flag</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Drop Table Scenario", key="btn_load_drop", use_container_width=True):
            load_scenario("drop_table")

    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Rehearsal Pipeline Architecture
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="margin-bottom:1.25rem;">
            <div style="font-size:1.35rem;font-weight:700;color:#F8FAFC;letter-spacing:-0.02em;">
                The 6-Stage Rehearsal Pipeline
            </div>
            <div style="font-size:0.9rem;color:#94A3B8;margin-top:2px;">
                How SchemaGuard isolates and proves migration safety without touching live data
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-size:0.75rem;font-weight:700;color:#6366F1;letter-spacing:0.05em;margin-bottom:0.4rem;">STAGE 01 & 02</div>
                <div style="font-weight:700;font-size:1rem;color:#F8FAFC;margin-bottom:0.35rem;">Clone & Static Parse</div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;">
                    Source opened strictly read-only. Database cloned into temporary sandbox via SQLite backup API. AST static analysis parses DDL with SQLGlot.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-size:0.75rem;font-weight:700;color:#3B82F6;letter-spacing:0.05em;margin-bottom:0.4rem;">STAGE 03 & 04</div>
                <div style="font-weight:700;font-size:1rem;color:#F8FAFC;margin-bottom:0.35rem;">Execute & Replay</div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;">
                    Migration applied exclusively to clone inside strict authorizer boundary. Application query contracts (OLD_APP & NEW_APP) replayed against post-migration DB.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-size:0.75rem;font-weight:700;color:#06B6D4;letter-spacing:0.05em;margin-bottom:0.4rem;">STAGE 05 & 06</div>
                <div style="font-weight:700;font-size:1rem;color:#F8FAFC;margin-bottom:0.35rem;">Invariants & Audit</div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;">
                    Domain assertions evaluated (must return 0 rows). Deep schema diff and row profiler detect anomalies. Deterministic JSON/Markdown evidence generated.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Core Principles
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

    with col_right:
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-weight:700;color:#F8FAFC;margin-bottom:0.4rem;display:flex;align-items:center;gap:6px;">
                    <span style="color:#22C55E;">🔒</span> Zero Production Touch
                </div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:1rem;">
                    Source databases are opened in read-only mode (<code>mode=ro</code>). All tests run inside disposable temporary clones.
                </div>
                <div style="font-weight:700;color:#F8FAFC;margin-bottom:0.4rem;display:flex;align-items:center;gap:6px;">
                    <span style="color:#6366F1;">⚖️</span> Honest Categorical Severity
                </div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:1rem;">
                    We never claim "guaranteed safe". A clean rehearsal is labeled <strong>"No configured checks failed"</strong>.
                </div>
                <div style="font-weight:700;color:#F8FAFC;margin-bottom:0.4rem;display:flex;align-items:center;gap:6px;">
                    <span style="color:#06B6D4;">📄</span> Audit-Ready Evidence
                </div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;">
                    Generate downloadable JSON and Markdown evidence packages ready to attach to GitHub/GitLab Pull Requests.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_footer()
