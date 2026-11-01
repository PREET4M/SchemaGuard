"""
ui/pages/rehearsal.py
---------------------
Migration rehearsal setup and execution page.

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
    """Render the complete migration rehearsal configuration page."""
    render_header(
        title="Rehearse Migration",
        subtitle="Configure the source database copy, migration DDL, query contracts, and domain invariants.",
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

    # If demo scenario was loaded from Overview, show notification
    if st.session_state.get("demo_loaded", False):
        scenario_name = st.session_state.get("scenario_name", "Demo Scenario")
        scenario_desc = st.session_state.get("scenario_description", "")
        success_box(f"Loaded {scenario_name}: {scenario_desc}")
        # Clear one-time banner
        st.session_state["demo_loaded"] = False

    # -----------------------------------------------------------------------
    # Step 1: Database Source Selection
    # -----------------------------------------------------------------------
    st.markdown("### 1. Source Database")
    st.caption("SchemaGuard will open this database strictly in read-only mode and copy it to an isolated sandbox.")

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
        
        # Display summary of tables and row counts
        try:
            conn = sqlite3.connect(f"file:{DEMO_DB_PATH.resolve()}?mode=ro", uri=True)
            cur = conn.cursor()
            tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
            counts: list[str] = []
            for t in tables:
                cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                counts.append(f"<code>{t}</code> ({cnt} rows)")
            conn.close()
            st.markdown(
                f"""
                <div style="background:#F1F5F9;border:1px solid #CBD5E1;border-radius:6px;padding:8px 12px;font-size:13px;color:#334155;margin-bottom:1rem;">
                    <strong>Demo Database Active:</strong> <code>data/demo/ecommerce.db</code> &nbsp;|&nbsp; Tables: {" • ".join(counts)}
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
            info_box("Upload a SQLite database file to begin, or switch back to the bundled Synthetic Demo.")
            return

    st.divider()

    # -----------------------------------------------------------------------
    # Step 2: Migration SQL DDL
    # -----------------------------------------------------------------------
    st.markdown("### 2. Migration SQL")
    st.caption("The proposed DDL/DML to rehearse exclusively against the isolated sandbox copy.")

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
        height=120,
        help="Multiple statements separated by semicolons are supported.",
    )
    st.session_state["migration_sql"] = migration_sql

    st.divider()

    # -----------------------------------------------------------------------
    # Step 3: Application Query Contracts & Domain Invariants
    # -----------------------------------------------------------------------
    st.markdown("### 3. Verification Contracts & Invariants")
    st.caption("Replayed read-only against the post-migration sandbox to ensure backward compatibility and data integrity.")

    tab_old, tab_new, tab_inv = st.tabs([
        "Production Contracts (OLD_APP)",
        "Upcoming Contracts (NEW_APP)",
        "Data Invariants (Assertions)",
    ])

    with tab_old:
        st.markdown(
            "**OLD_APP Contracts:** Read-only queries executed by currently deployed application code. "
            "If any of these fail post-migration, SchemaGuard flags an immediate **CRITICAL** risk."
        )
        old_contracts_text = st.text_area(
            "Old Application SQL Queries (one or more queries):",
            value=st.session_state.get("old_contracts_sql", ""),
            height=100,
            key="input_old_contracts",
        )
        st.session_state["old_contracts_sql"] = old_contracts_text

    with tab_new:
        st.markdown(
            "**NEW_APP Contracts:** Read-only queries planned for the upcoming application release "
            "expecting new tables or columns. If these fail, SchemaGuard flags **MODERATE** risk."
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
            "**Data Invariants:** SQL queries that search for invalid data or constraint violations. "
            "**Rule: The query must return 0 violating rows to PASS.** Any returned rows indicate data corruption."
        )
        invariants_text = st.text_area(
            "Data Invariant Queries (use '-- Invariant Name' before each query):",
            value=st.session_state.get("invariants_sql", ""),
            height=130,
            key="input_invariants",
        )
        st.session_state["invariants_sql"] = invariants_text

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Step 4: Rehearsal Trigger
    # -----------------------------------------------------------------------
    col_btn, col_info = st.columns([1, 2])

    with col_btn:
        run_clicked = st.button(
            "🚀 Run Migration Rehearsal",
            type="primary",
            use_container_width=True,
        )

    with col_info:
        st.markdown(
            "<div style='font-size:12px;color:#64748B;line-height:1.4;padding-top:4px;'>"
            "Executes exclusively inside a temporary copy. Source database is never modified. "
            "Generates comprehensive JSON & Markdown evidence reports.</div>",
            unsafe_allow_html=True,
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
