"""
app.py
------
SchemaGuard — Premium Migration Rehearsal Engine
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
# Session State & Navigation Management
# ---------------------------------------------------------------------------

PAGES = ["Overview", "Rehearsal", "Results", "Settings"]

if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Overview"

# ---------------------------------------------------------------------------
# Floating Dark Sidebar (Linear / Raycast Grade)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:0.65rem;margin-bottom:0.35rem;">
            <div style="width:34px;height:34px;background:linear-gradient(135deg, #6366F1, #06B6D4);border-radius:8px;display:flex;align-items:center;justify-content:center;box-shadow:0 0 16px rgba(99,102,241,0.5);font-size:1.15rem;">
                🛡️
            </div>
            <div>
                <span style="font-size:1.25rem;font-weight:800;color:#F8FAFC;letter-spacing:-0.03em;">SchemaGuard</span>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:1.5rem;">
            <span style="font-size:0.68rem;font-weight:700;color:#A5B4FC;background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.3);padding:2px 8px;border-radius:9999px;letter-spacing:0.04em;">
                v2.0 • LOCAL-FIRST
            </span>
            <span style="font-size:0.68rem;font-weight:600;color:#22C55E;background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.25);padding:2px 6px;border-radius:9999px;">
                ● READY
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_idx = PAGES.index(st.session_state["active_page"]) if st.session_state["active_page"] in PAGES else 0

    selected_page = st.radio(
        "Navigation Menu",
        options=PAGES,
        index=current_idx,
        label_visibility="collapsed",
    )

    if selected_page != st.session_state["active_page"]:
        st.session_state["active_page"] = selected_page
        st.rerun()

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # Rehearsal session status card in sidebar
    report = st.session_state.get("rehearsal_report")
    if report is not None:
        sev_val = report.severity.value.lower()
        if sev_val == "critical":
            status_color = "#EF4444"
            status_bg = "rgba(239, 68, 68, 0.12)"
            status_border = "rgba(239, 68, 68, 0.3)"
        elif sev_val == "high":
            status_color = "#F97316"
            status_bg = "rgba(249, 115, 22, 0.12)"
            status_border = "rgba(249, 115, 22, 0.3)"
        elif sev_val in ("moderate", "warning"):
            status_color = "#EAB308"
            status_bg = "rgba(234, 179, 8, 0.12)"
            status_border = "rgba(234, 179, 8, 0.3)"
        else:
            status_color = "#22C55E"
            status_bg = "rgba(34, 197, 94, 0.12)"
            status_border = "rgba(34, 197, 94, 0.3)"

        st.markdown(
            f"""
            <div style="background:rgba(22, 27, 38, 0.8);border:1px solid rgba(255, 255, 255, 0.08);border-radius:10px;padding:12px;margin-bottom:1rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                <div style="font-size:0.68rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">
                    Active Rehearsal Result
                </div>
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="background:{status_bg};color:{status_color};border:1px solid {status_border};padding:1px 8px;border-radius:9999px;font-size:10px;font-weight:700;">
                        {report.severity.value.upper()}
                    </span>
                    <span style="font-size:11px;color:#94A3B8;font-family:monospace;">
                        {round(report.migration_result.elapsed_total_ms, 1)}ms
                    </span>
                </div>
                <div style="font-size:0.75rem;color:#E2E8F0;line-height:1.35;margin-top:4px;">
                    {report.label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_view, col_clear = st.columns(2)
        with col_view:
            if st.button("View Audit", use_container_width=True):
                st.session_state["active_page"] = "Results"
                st.rerun()
        with col_clear:
            if st.button("Reset", use_container_width=True):
                st.session_state.pop("rehearsal_report", None)
                st.session_state["active_page"] = "Overview"
                st.rerun()

    st.markdown(
        """
        <div style="font-size:0.72rem;color:#64748B;line-height:1.45;margin-top:3rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.06);">
            <strong>Zero Production Writes</strong><br>
            All rehearsals run exclusively inside temporary SQLite clones.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Top Bar Navigation Breadcrumb
# ---------------------------------------------------------------------------

active = st.session_state["active_page"]

st.markdown(
    f"""
    <div style="display:flex;align-items:center;justify-content:space-between;padding:0.75rem 0;margin-bottom:0.5rem;border-bottom:1px solid rgba(255,255,255,0.06);font-size:13px;color:#64748B;">
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="color:#94A3B8;">SchemaGuard</span>
            <span>/</span>
            <span style="color:#F8FAFC;font-weight:600;">{active}</span>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-family:monospace;font-size:11px;color:#64748B;">SQLITE • LOCAL</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Main Page Router
# ---------------------------------------------------------------------------

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
