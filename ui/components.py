"""
ui/components.py
----------------
Reusable Streamlit widget helpers and layout components for SchemaGuard.

Each component generates restrained, developer-grade markup with zero unnecessary
animations, explicit status markers, and strict adherence to the design system.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import (
    COLOR_BG,
    COLOR_CARD_BORDER,
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_NEUTRAL,
    COLOR_SUCCESS,
    COLOR_WARNING,
    SEVERITY_BG_COLORS,
    SEVERITY_BORDER_COLORS,
    SEVERITY_COLORS,
    SEVERITY_LABELS,
    STATUS_BG_COLORS,
    STATUS_BORDER_COLORS,
    STATUS_COLORS,
    STATUS_ICONS,
)


# ---------------------------------------------------------------------------
# Page / Hero Header
# ---------------------------------------------------------------------------

def render_header(
    title: str = "Know what breaks before it ships.",
    subtitle: str = "Rehearse database migrations against an isolated copy. Verify application compatibility with evidence.",
) -> None:
    """Render the standard SchemaGuard hero banner."""
    st.markdown(
        f"""
        <div class="sg-hero-header">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.25rem;">
                <span style="font-size:1.6rem;line-height:1;">🛡️</span>
                <span class="sg-hero-title">{title}</span>
            </div>
            <div class="sg-hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Badges & Status Indicators
# ---------------------------------------------------------------------------

def severity_badge(severity: str, custom_label: str | None = None) -> None:
    """Render a coloured inline pill badge for a Severity level.
    
    For LOW severity, defaults to 'No configured checks failed'.
    """
    sev_key = str(severity).lower()
    color = SEVERITY_COLORS.get(sev_key, COLOR_NEUTRAL)
    bg = SEVERITY_BG_COLORS.get(sev_key, "#F3F4F6")
    border = SEVERITY_BORDER_COLORS.get(sev_key, "#E5E7EB")
    
    if custom_label:
        label = custom_label
    else:
        label = SEVERITY_LABELS.get(sev_key, sev_key.upper())

    st.markdown(
        f'<span style="background:{bg};color:{color};border:1px solid {border};'
        f'padding:3px 10px;border-radius:9999px;font-size:12px;font-weight:600;'
        f'letter-spacing:0.03em;display:inline-flex;align-items:center;">{label}</span>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    """Render a coloured status pill badge for a check or contract outcome."""
    stat_key = str(status).lower()
    color = STATUS_COLORS.get(stat_key, COLOR_NEUTRAL)
    bg = STATUS_BG_COLORS.get(stat_key, "#F3F4F6")
    border = STATUS_BORDER_COLORS.get(stat_key, "#E5E7EB")
    icon = STATUS_ICONS.get(stat_key, "•")
    label = str(status).upper()

    st.markdown(
        f'<span style="background:{bg};color:{color};border:1px solid {border};'
        f'padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:600;'
        f'letter-spacing:0.04em;display:inline-flex;align-items:center;gap:4px;">'
        f'<span>{icon}</span><span>{label}</span></span>',
        unsafe_allow_html=True,
    )


def diff_badge(kind: str) -> str:
    """Return inline HTML badge for schema diff actions (+, -, ~)."""
    kind_upper = kind.upper()
    if kind_upper in ("ADDED", "ADD", "+"):
        return '<span class="sg-diff-add">+ ADDED</span>'
    elif kind_upper in ("REMOVED", "DROP", "-"):
        return '<span class="sg-diff-remove">- REMOVED</span>'
    else:
        return '<span class="sg-diff-modify">~ MODIFIED</span>'


# ---------------------------------------------------------------------------
# Callout Banners
# ---------------------------------------------------------------------------

def info_box(message: str) -> None:
    """Render a blue informational callout."""
    st.markdown(
        f'<div class="sg-callout sg-callout-info">{message}</div>',
        unsafe_allow_html=True,
    )


def warning_box(message: str) -> None:
    """Render an amber warning callout."""
    st.markdown(
        f'<div class="sg-callout sg-callout-warning">{message}</div>',
        unsafe_allow_html=True,
    )


def error_box(message: str) -> None:
    """Render a red error callout."""
    st.markdown(
        f'<div class="sg-callout sg-callout-danger">{message}</div>',
        unsafe_allow_html=True,
    )


def success_box(message: str) -> None:
    """Render an emerald success callout."""
    st.markdown(
        f'<div class="sg-callout sg-callout-success">{message}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metrics & Structure Helpers
# ---------------------------------------------------------------------------

def metric_tile(label: str, value: str | int | float, subtext: str | None = None) -> None:
    """Render a single developer-grade metric tile."""
    sub_html = f'<div style="font-size:11px;color:#64748B;margin-top:2px;">{subtext}</div>' if subtext else ""
    st.markdown(
        f"""
        <div class="sg-stat-tile">
            <span class="sg-stat-label">{label}</span>
            <span class="sg-stat-value">{value}</span>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_row(metrics: dict[str, str | int | float]) -> None:
    """Render a horizontal row of stat tiles."""
    cols = st.columns(len(metrics))
    for col, (label, val) in zip(cols, metrics.items()):
        with col:
            metric_tile(label, val)


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section heading with subtle border."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


def code_snippet(code: str, language: str = "sql") -> None:
    """Display monospaced SQL or code inside a clean code block."""
    st.code(code.strip(), language=language)


def render_footer() -> None:
    """Render subtle footer reminding user of safety bounds."""
    st.markdown(
        """
        <div style="margin-top:3rem;padding-top:1.5rem;border-top:1px solid #E2E8F0;font-size:12px;color:#64748B;display:flex;justify-content:space-between;align-items:center;">
            <div>SchemaGuard • Local-First SQLite Migration Rehearsal & Compatibility Engine</div>
            <div>Never executes against production databases • Sandboxed via SQLite backup API</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
