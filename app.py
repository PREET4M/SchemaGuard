"""
app.py
------
SchemaGuard — Migration Rehearsal Engine
Entry point for the Streamlit application.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from schemaguard.config import APP_ICON, APP_LAYOUT, APP_TITLE

# ---------------------------------------------------------------------------
# Page configuration — must be the first Streamlit call in the script
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title(f"{APP_ICON} {APP_TITLE}")
st.caption(
    "Rehearse SQLite migrations in an isolated sandbox before touching production data."
)
st.divider()

# ---------------------------------------------------------------------------
# Landing content
# ---------------------------------------------------------------------------

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(
        """
        ### What SchemaGuard does

        1. **Copies** your database into a throw-away sandbox — the original is never touched.
        2. **Applies** your proposed migration SQL to the sandbox copy.
        3. **Replays** your application query contracts and checks they still work.
        4. **Evaluates** SQL invariants (e.g. *no negative totals*, *no orphaned rows*).
        5. **Diffs** the pre- and post-migration schema and row counts.
        6. **Generates** a deterministic, evidence-backed report you can attach to a PR.

        > ⚠️ SchemaGuard is a rehearsal tool. It reduces risk but **cannot guarantee safety**.
        > Always review the generated report and test in a staging environment.
        """
    )

with col_right:
    st.info(
        "**Get started**\n\n"
        "Use the sidebar to navigate to the **Rehearsal** page, upload your database "
        "and migration SQL, then run the checks.",
        icon="👈",
    )

# ---------------------------------------------------------------------------
# Quick-stats placeholder (populated once a rehearsal has run)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Recent Runs")
st.markdown(
    "_No rehearsals have been run yet in this session. "
    "Results will appear here after your first run._"
)

