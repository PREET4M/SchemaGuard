"""
ui/pages/settings.py
--------------------
System settings, sandbox limits, and security configuration inspector.

Provides complete transparency into:
  - File size limits and query execution timeouts.
  - Active SQLite connection pragmas.
  - Set_authorizer callback security boundaries.
  - Local Python, SQLite, and dependency environment details.
"""

from __future__ import annotations

import platform
import sqlite3
import sys
import sqlglot
import streamlit as st

from schemaguard.config import (
    MAX_SAMPLE_ROWS,
    MAX_UPLOAD_SIZE_MB,
    QUERY_TIMEOUT_SECONDS,
    SANDBOX_DB_FILENAME,
    SANDBOX_DIR,
    SANDBOX_PRAGMAS,
)
from ui.components import (
    info_box,
    render_footer,
    render_header,
    section_header,
    success_box,
)


def render_settings_page() -> None:
    """Render the Apple / Linear inspired settings and security parameters page."""
    render_header(
        title="Settings & System Limits",
        subtitle="Transparent overview of sandbox constraints, security boundaries, and execution environment.",
        badge_text="TRANSPARENT BOUNDARIES",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.85rem;">
                Execution Constraints
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="sg-card">
                <table style="width:100%;font-size:0.88rem;border-collapse:collapse;">
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);padding:8px 0;">
                        <td style="padding:8px 0;color:#94A3B8;">Max Upload Size</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{MAX_UPLOAD_SIZE_MB} MB</td>
                    </tr>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);padding:8px 0;">
                        <td style="padding:8px 0;color:#94A3B8;">Statement Timeout</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{QUERY_TIMEOUT_SECONDS} seconds</td>
                    </tr>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);padding:8px 0;">
                        <td style="padding:8px 0;color:#94A3B8;">Max Sample Rows</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{MAX_SAMPLE_ROWS} rows</td>
                    </tr>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);padding:8px 0;">
                        <td style="padding:8px 0;color:#94A3B8;">Sandbox Directory</td>
                        <td style="padding:8px 0;font-weight:700;color:#A5B4FC;text-align:right;font-family:monospace;">{SANDBOX_DIR}/</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#94A3B8;">Sandbox Clone File</td>
                        <td style="padding:8px 0;font-weight:700;color:#A5B4FC;text-align:right;font-family:monospace;">{SANDBOX_DB_FILENAME}</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin:1.5rem 0 0.85rem 0;">
                SQLite Connection Pragmas
            </div>
            """,
            unsafe_allow_html=True,
        )
        pragma_rows = "".join(
            f"<tr style='border-bottom:1px solid rgba(255,255,255,0.08);'><td style='padding:8px 0;color:#94A3B8;'>PRAGMA {k}</td><td style='padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;'>{v}</td></tr>"
            for k, v in SANDBOX_PRAGMAS.items()
        )
        st.markdown(
            f"""
            <div class="sg-card">
                <table style="width:100%;font-size:0.88rem;border-collapse:collapse;">
                    {pragma_rows}
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin-bottom:0.85rem;">
                Security Authorizer Boundary
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-weight:700;font-size:0.95rem;color:#F8FAFC;margin-bottom:0.4rem;">
                    Blocked SQLite Operations
                </div>
                <div style="font-size:0.85rem;color:#94A3B8;line-height:1.45;margin-bottom:0.85rem;">
                    During migration execution and contract replay, SQLite's low-level <code>set_authorizer</code>
                    callback strictly blocks attempts to breach the sandbox:
                </div>
                <ul style="font-size:0.85rem;color:#CBD5E1;padding-left:1.2rem;margin-bottom:0;line-height:1.7;">
                    <li><strong>SQLITE_ATTACH / DETACH</strong>: Blocked from referencing external databases.</li>
                    <li><strong>PRAGMA writable_schema</strong>: Blocked to prevent raw catalog corruption.</li>
                    <li><strong>sqlite3_enable_load_extension</strong>: Blocked to prevent loading unvetted native binaries.</li>
                    <li><strong>Write operations during Contract Replay</strong>: Read-only contracts are blocked from executing INSERT, UPDATE, DELETE, or DDL.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="font-size:1.15rem;font-weight:700;color:#F8FAFC;margin:1.5rem 0 0.85rem 0;">
                Runtime Environment
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="sg-card">
                <table style="width:100%;font-size:0.88rem;border-collapse:collapse;">
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
                        <td style="padding:8px 0;color:#94A3B8;">Python Runtime</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{platform.python_version()}</td>
                    </tr>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
                        <td style="padding:8px 0;color:#94A3B8;">SQLite Engine</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{sqlite3.sqlite_version}</td>
                    </tr>
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
                        <td style="padding:8px 0;color:#94A3B8;">SQLGlot Parser</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{sqlglot.__version__}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#94A3B8;">Streamlit Version</td>
                        <td style="padding:8px 0;font-weight:700;color:#F8FAFC;text-align:right;font-family:monospace;">{st.__version__}</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        success_box(
            "🔒 <strong>Local-First Guarantee:</strong> Zero telemetry, zero network calls, "
            "zero external LLM dependencies, zero cloud database connections."
        )

    render_footer()
