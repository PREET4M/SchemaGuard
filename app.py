"""
app.py
------
SchemaGuard — Migration Rehearsal Engine
Streamlit Web Application Entry Point.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from schemaguard.config import APP_ICON, APP_LAYOUT, APP_TITLE
from ui.pages.overview import render_overview_page
from ui.pages.rehearsal import render_rehearsal_page
from ui.pages.results import render_results_page
from ui.pages.settings import render_settings_page

# ---------------------------------------------------------------------------
# Streamlit page configuration (must precede any other st commands)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load Custom Stylesheet
# ---------------------------------------------------------------------------

CSS_PATH = Path("ui/styles/main.css")
if CSS_PATH.exists():
    css_content = CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session State Management
# ---------------------------------------------------------------------------

PAGES = ["Overview", "Rehearsal", "Results", "Settings"]

if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Overview"

# ---------------------------------------------------------------------------
# Sidebar Navigation & Branding
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.25rem;">
            <span style="font-size:1.6rem;line-height:1;">🛡️</span>
            <span style="font-size:1.25rem;font-weight:700;color:#0F172A;letter-spacing:-0.02em;">SchemaGuard</span>
        </div>
        <div style="font-size:0.75rem;font-weight:600;color:#2563EB;background:#EFF6FF;border:1px solid #BFDBFE;padding:2px 8px;border-radius:9999px;display:inline-block;margin-bottom:1rem;">
            LOCAL-FIRST • SQLITE
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_idx = PAGES.index(st.session_state["active_page"]) if st.session_state["active_page"] in PAGES else 0

    selected_page = st.radio(
        "Navigation",
        options=PAGES,
        index=current_idx,
        label_visibility="collapsed",
    )

    if selected_page != st.session_state["active_page"]:
        st.session_state["active_page"] = selected_page
        st.rerun()

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # Rehearsal session status widget
    report = st.session_state.get("rehearsal_report")
    if report is not None:
        st.markdown(
            f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px;margin-bottom:1rem;">
                <div style="font-size:0.7rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">
                    Latest Rehearsal
                </div>
                <div style="font-size:0.85rem;font-weight:600;color:#0F172A;margin-bottom:2px;">
                    {report.severity.value.upper()}
                </div>
                <div style="font-size:0.75rem;color:#475569;line-height:1.3;">
                    {report.label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Clear Results", use_container_width=True):
            st.session_state.pop("rehearsal_report", None)
            st.session_state["active_page"] = "Overview"
            st.rerun()

    st.markdown(
        """
        <div style="font-size:0.75rem;color:#94A3B8;line-height:1.4;margin-top:2rem;">
            <strong>Never touches original DB.</strong><br>
            All rehearsals run exclusively inside temporary SQLite sandboxes.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Main Page Router
# ---------------------------------------------------------------------------

active = st.session_state["active_page"]

if active == "Overview":
    render_overview_page()
elif active == "Rehearsal":
    render_rehearsal_page()
elif active == "Results":
    render_results_page()
elif active == "Settings":
    render_settings_page()
else:
    render_overview_page()
