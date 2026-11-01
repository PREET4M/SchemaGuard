"""
ui/pages/rehearsal.py
---------------------
Migration rehearsal workspace — professional developer studio.

Enables developers to:
  1. Select the database source (bundled synthetic demo DB or custom upload).
  2. Provide migration SQL (custom editor or curated scenario presets).
  3. Define OLD_APP and NEW_APP query contracts to verify application compatibility.
  4. Define business domain invariants (assertions that must return 0 violating rows).
  5. Trigger execution against an isolated sandbox and view live results.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import streamlit as st

from schemaguard.config import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB, SANDBOX_DIR
from schemaguard.core.orchestrator import rehearse_migration
from ui.components import (
    error_box,
    info_box,
    render_footer,
    render_header,
    section_header,
    success_box,
    warning_box,
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


def _split_queries(sql_text: str) -> list[str]:
    """Split multi-query text by semicolons while ignoring empty lines and pure comments."""
    statements: list[str] = []
    current: list[str] = []

    for line in sql_text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("--"):
            continue
        current.append(line)
        if ";" in line:
            full_stmt = "\n".join(current).strip()
            if full_stmt:
                statements.append(full_stmt)
            current = []

    if current:
        trailing = "\n".join(current).strip()
        if trailing:
            statements.append(trailing)

    return statements


def render_rehearsal_page() -> None:
    """Render the Apple / Linear inspired migration rehearsal workspace."""
    render_header(
        title="Migration Rehearsal",
        subtitle="Configure the source database copy, migration DDL, query contracts, and domain invariants.",
        badge_text="ISOLATED ENVIRONMENT",
    )

    # Initialize session state defaults if absent
    if "db_source_type" not in st.session_state:
        st.session_state["db_source_type"] = "demo"
    if "migration_preset" not in st.session_state:
        st.session_state["migration_preset"] = "custom"
    if "migration_sql" not in st.session_state:
        st.session_state["migration_sql"] = _read_file_safe(MIGRATION_DIR / "01_safe_add_column.sql")
    if "old_contracts_sql" not in st.session_state:
        st.session_state["old_contracts_sql"] = _read_file_safe(CONTRACTS_DIR / "old_app.sql")
    if "new_contracts_sql" not in st.session_state:
        st.session_state["new_contracts_sql"] = _read_file_safe(CONTRACTS_DIR / "new_app.sql")
    if "invariants_sql" not in st.session_state:
        st.session_state["invariants_sql"] = _read_file_safe(INVARIANTS_DIR / "invariants.sql")

    # If demo scenario was loaded from Overview, show high-impact notification
    if st.session_state.get("demo_loaded", False):
        scenario_name = st.session_state.get("scenario_name", "Demo Scenario")
        scenario_desc = st.session_state.get("scenario_description", "")
        success_box(f"<strong>Loaded Preset:</strong> {scenario_name} — {scenario_desc}")
        st.session_state["demo_loaded"] = False

    # -----------------------------------------------------------------------
    # Step 1: Database Source Selection
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.25rem;">
            1. Source Database Clone
        </div>
        <div style="font-size:0.85rem;color:#94A3B8;margin-bottom:0.85rem;">
            Opened strictly in read-only mode (<code>mode=ro</code>) and backed up to an isolated temporary sandbox.
        </div>
        """,
        unsafe_allow_html=True,
    )

    db_option = st.radio(
        "Choose database origin:",
        options=["Synthetic E-Commerce Demo (ecommerce.db)", "Upload Custom SQLite Database"],
        index=0 if st.session_state.get("db_source_type") == "demo" else 1,
        horizontal=True,
    )

    source_db_path: Path | None = None

    if "Synthetic" in db_option:
        st.session_state["db_source_type"] = "demo"
        if not DEMO_DB_PATH.exists():
            error_box(f"Demo database not found at `{DEMO_DB_PATH}`. Please run `python scripts/create_demo_db.py`.")
            return
        source_db_path = DEMO_DB_PATH

        # Display live chip inspection of tables and row counts
        try:
            conn = sqlite3.connect(f"file:{DEMO_DB_PATH.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            tables = [
                row[0]
                for row in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            ]
            chips_html: list[str] = []
            for t in tables:
                cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                chips_html.append(
                    f'<span style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);'
                    f'padding:3px 8px;border-radius:6px;font-size:12px;font-family:monospace;color:#E2E8F0;">'
                    f'{t} <span style="color:#6366F1;font-weight:700;">({cnt})</span></span>'
                )
            conn.close()

            st.markdown(
                f"""
                <div class="sg-card" style="padding:0.85rem 1.15rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap;">
                    <span style="font-size:0.8rem;font-weight:700;color:#A5B4FC;text-transform:uppercase;letter-spacing:0.04em;">Tables & Row Counts:</span>
                    {" ".join(chips_html)}
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.warning(f"Could not inspect demo database metadata: {e}")
    else:
        st.session_state["db_source_type"] = "upload"
        uploaded_file = st.file_uploader(
            "Upload SQLite database file (.db, .sqlite, .sqlite3)",
            type=["db", "sqlite", "sqlite3"],
            help=f"Maximum accepted file size is {MAX_UPLOAD_SIZE_MB} MB.",
        )
        if uploaded_file is not None:
            if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
                error_box(f"File size exceeds maximum permitted limit of {MAX_UPLOAD_SIZE_MB} MB.")
                return

            upload_dir = Path(SANDBOX_DIR) / "staging"
            upload_dir.mkdir(parents=True, exist_ok=True)
            staged_path = upload_dir / uploaded_file.name
            staged_path.write_bytes(uploaded_file.getbuffer())
            source_db_path = staged_path
            success_box(f"Uploaded `{uploaded_file.name}` ({round(uploaded_file.size / 1024, 1)} KB) ready for rehearsal.")
        else:
            info_box("Upload a SQLite database file to begin, or select the synthetic demo.")
            return

    st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin:1.5rem 0;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Step 2: Migration SQL DDL
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.25rem;">
            2. Migration SQL Workspace
        </div>
        <div style="font-size:0.85rem;color:#94A3B8;margin-bottom:0.85rem;">
            The proposed DDL/DML to execute exclusively against the isolated sandbox copy.
        </div>
        """,
        unsafe_allow_html=True,
    )

    preset_col1, preset_col2 = st.columns([1, 2])
    with preset_col1:
        preset_choice = st.selectbox(
            "Select Preset or Custom:",
            options=[
                "Custom SQL",
                "01_safe_add_column.sql (Safe: Add phone)",
                "02_break_old_query.sql (Breaking: Drop email)",
                "03_drop_table.sql (Destructive: Drop order_items)",
            ],
            index=0,
        )

    # Preset selection triggers SQL update
    if preset_choice.startswith("01_"):
        preset_sql = _read_file_safe(MIGRATION_DIR / "01_safe_add_column.sql")
        if st.session_state.get("migration_preset") != "01":
            st.session_state["migration_sql"] = preset_sql
            st.session_state["migration_preset"] = "01"
    elif preset_choice.startswith("02_"):
        preset_sql = _read_file_safe(MIGRATION_DIR / "02_break_old_query.sql")
        if st.session_state.get("migration_preset") != "02":
            st.session_state["migration_sql"] = preset_sql
            st.session_state["migration_preset"] = "02"
    elif preset_choice.startswith("03_"):
        preset_sql = _read_file_safe(MIGRATION_DIR / "03_drop_table.sql")
        if st.session_state.get("migration_preset") != "03":
            st.session_state["migration_sql"] = preset_sql
            st.session_state["migration_preset"] = "03"
    elif preset_choice == "Custom SQL":
        st.session_state["migration_preset"] = "custom"

    migration_sql = st.text_area(
        "Migration SQL Statements:",
        value=st.session_state.get("migration_sql", ""),
        height=140,
        help="Multiple statements separated by semicolons are supported.",
    )
    st.session_state["migration_sql"] = migration_sql

    st.markdown("<div style='height:1px;background:rgba(255,255,255,0.08);margin:1.5rem 0;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Step 3: Application Query Contracts & Domain Invariants
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.25rem;">
            3. Verification Contracts & Domain Invariants
        </div>
        <div style="font-size:0.85rem;color:#94A3B8;margin-bottom:0.85rem;">
            Replayed read-only against the post-migration sandbox to verify application compatibility.
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_old, tab_new, tab_inv = st.tabs([
        "Production Contracts (OLD_APP)",
        "Upcoming Contracts (NEW_APP)",
        "Business Invariants (Assertions)",
    ])

    with tab_old:
        st.markdown(
            "<div style='font-size:0.85rem;color:#94A3B8;margin-bottom:0.5rem;'>"
            "<strong>OLD_APP Contracts:</strong> Queries currently running in production. "
            "If any fail post-migration, SchemaGuard flags an immediate <strong>CRITICAL</strong> risk.</div>",
            unsafe_allow_html=True,
        )
        old_contracts_text = st.text_area(
            "Old Application SQL Queries:",
            value=st.session_state.get("old_contracts_sql", ""),
            height=100,
            key="input_old_contracts",
        )
        st.session_state["old_contracts_sql"] = old_contracts_text

    with tab_new:
        st.markdown(
            "<div style='font-size:0.85rem;color:#94A3B8;margin-bottom:0.5rem;'>"
            "<strong>NEW_APP Contracts:</strong> Queries expected by the upcoming application version. "
            "If these fail, SchemaGuard flags a <strong>MODERATE</strong> risk.</div>",
            unsafe_allow_html=True,
        )
        new_contracts_text = st.text_area(
            "New Application SQL Queries:",
            value=st.session_state.get("new_contracts_sql", ""),
            height=100,
            key="input_new_contracts",
        )
        st.session_state["new_contracts_sql"] = new_contracts_text

    with tab_inv:
        st.markdown(
            "<div style='font-size:0.85rem;color:#94A3B8;margin-bottom:0.5rem;'>"
            "<strong>Data Invariants:</strong> Assertions that search for corrupted or orphaned records. "
            "<strong>Rule: Must return 0 violating rows to PASS.</strong> Any returned rows flag violations.</div>",
            unsafe_allow_html=True,
        )
        invariants_text = st.text_area(
            "Data Invariant Queries (use '-- Invariant Name' before each query):",
            value=st.session_state.get("invariants_sql", ""),
            height=120,
            key="input_invariants",
        )
        st.session_state["invariants_sql"] = invariants_text

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Step 4: Rehearsal Trigger Action Bar
    # -----------------------------------------------------------------------
    st.markdown(
        """
        <div class="sg-card" style="padding:1.25rem 1.5rem;display:flex;align-items:center;justify-content:space-between;gap:1.5rem;">
            <div>
                <div style="font-weight:700;font-size:1.05rem;color:#F8FAFC;margin-bottom:2px;">
                    Ready for Rehearsal Execution
                </div>
                <div style="font-size:0.82rem;color:#94A3B8;">
                    Source DB is isolated with zero writes. All tests execute inside a temporary clone.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    run_clicked = st.button(
        "⚡ Execute Migration Rehearsal",
        type="primary",
        use_container_width=True,
    )

    if run_clicked:
        if not source_db_path or not source_db_path.exists():
            error_box("Invalid source database file. Please ensure a valid database is selected.")
            return

        if not migration_sql.strip():
            error_box("Migration SQL cannot be empty. Please enter one or more SQL statements.")
            return

        # Prepare normalized inputs
        old_queries = _split_queries(old_contracts_text) if old_contracts_text.strip() else []
        new_queries = _split_queries(new_contracts_text) if new_contracts_text.strip() else []
        invariants_list = [invariants_text.strip()] if invariants_text.strip() else []

        with st.spinner("Rehearsing migration in isolated sandbox..."):
            try:
                report = rehearse_migration(
                    source_db_path=source_db_path,
                    migration_sql=migration_sql,
                    old_app_contracts=old_queries,
                    new_app_contracts=new_queries,
                    invariants=invariants_list,
                )
                st.session_state["rehearsal_report"] = report
                st.session_state["active_page"] = "Results"
                st.rerun()
            except Exception as e:
                error_box(f"Rehearsal failed before completing checks: {e}")

    render_footer()
