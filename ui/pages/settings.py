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
    """Render the SchemaGuard settings and security parameters page."""
    render_header(
        title="Settings & System Limits",
        subtitle="Transparent overview of sandbox constraints, security boundaries, and execution environment.",
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Execution Constraints")
        st.markdown(
            f"""
            <div class="sg-card">
                <table style="width:100%;font-size:0.88rem;border-collapse:collapse;">
                    <tr style="border-bottom:1px solid #E2E8F0;padding:6px 0;">
                        <td style="padding:6px 0;color:#64748B;">Max Database Size</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;">{MAX_UPLOAD_SIZE_MB} MB</td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0;padding:6px 0;">
                        <td style="padding:6px 0;color:#64748B;">Statement Timeout</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;">{QUERY_TIMEOUT_SECONDS} seconds</td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0;padding:6px 0;">
                        <td style="padding:6px 0;color:#64748B;">Max Sample Rows</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;">{MAX_SAMPLE_ROWS} rows</td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0;padding:6px 0;">
                        <td style="padding:6px 0;color:#64748B;">Sandbox Directory</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{SANDBOX_DIR}/</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#64748B;">Sandbox Clone File</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{SANDBOX_DB_FILENAME}</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### SQLite Connection Pragmas")
        st.markdown(
            """
            Applied immediately upon opening each sandbox connection:
            """
        )
        pragma_rows = "".join(
            f"<tr style='border-bottom:1px solid #E2E8F0;'><td style='padding:6px 0;color:#64748B;'>PRAGMA {k}</td><td style='padding:6px 0;font-weight:600;text-align:right;font-family:monospace;'>{v}</td></tr>"
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
        st.markdown("### Security Authorizer Boundary")
        st.markdown(
            """
            <div class="sg-card">
                <div style="font-weight:600;font-size:0.92rem;color:#0F172A;margin-bottom:0.4rem;">
                    Blocked SQLite Operations
                </div>
                <div style="font-size:0.85rem;color:#334155;line-height:1.45;margin-bottom:0.75rem;">
                    During migration execution and contract replay, SQLite's low-level <code>set_authorizer</code>
                    callback strictly blocks attempts to breach the sandbox:
                </div>
                <ul style="font-size:0.85rem;color:#334155;padding-left:1.2rem;margin-bottom:0;">
                    <li><strong>SQLITE_ATTACH / DETACH</strong>: Blocked from referencing external databases.</li>
                    <li><strong>PRAGMA writable_schema</strong>: Blocked to prevent raw catalog corruption.</li>
                    <li><strong>sqlite3_enable_load_extension</strong>: Blocked to prevent loading unvetted native binaries.</li>
                    <li><strong>Write operations during Contract Replay</strong>: Read-only contracts are blocked from executing INSERT, UPDATE, DELETE, or DDL.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Runtime Environment")
        st.markdown(
            f"""
            <div class="sg-card">
                <table style="width:100%;font-size:0.88rem;border-collapse:collapse;">
                    <tr style="border-bottom:1px solid #E2E8F0;">
                        <td style="padding:6px 0;color:#64748B;">Python Runtime</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{platform.python_version()}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0;">
                        <td style="padding:6px 0;color:#64748B;">SQLite Engine</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{sqlite3.sqlite_version}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #E2E8F0;">
                        <td style="padding:6px 0;color:#64748B;">SQLGlot Parser</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{sqlglot.__version__}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#64748B;">Streamlit Version</td>
                        <td style="padding:6px 0;font-weight:600;text-align:right;font-family:monospace;">{st.__version__}</td>
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
