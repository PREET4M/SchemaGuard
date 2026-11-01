"""
ui/components.py
----------------
Reusable high-end UI components and layout widgets for SchemaGuard.

Design Principles:
  - Apple / Linear / Raycast-inspired dark glass surfaces
  - Atmospheric depth, subtle border reflections, and refined typography
  - Strict absence of misleading claims: LOW severity is always labeled
    "No configured checks failed", never "guaranteed safe"
  - Micro-interactions and accessible markup
"""

from __future__ import annotations

import streamlit as st

from ui.theme import (
    COLOR_BORDER_GLASS,
    COLOR_CRITICAL,
    COLOR_INFO,
    COLOR_LOW,
    COLOR_MODERATE,
    COLOR_NEUTRAL,
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
    badge_text: str | None = None,
) -> None:
    """Render the Apple-grade editorial hero banner."""
    badge_html = f'<div class="sg-pill-badge">{badge_text}</div>' if badge_text else ""
    st.markdown(
        f"""
        <div class="sg-hero-section">
            {badge_html}
            <div class="sg-hero-title">{title}</div>
            <div class="sg-hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Badges & Status Indicators
# ---------------------------------------------------------------------------

def severity_badge(severity: str, custom_label: str | None = None) -> None:
    """Render a coloured inline glowing pill badge for a Severity level.
    
    For LOW severity, strictly displays 'No configured checks failed'.
    """
    sev_key = str(severity).lower()
    color = SEVERITY_COLORS.get(sev_key, COLOR_NEUTRAL)
    bg = SEVERITY_BG_COLORS.get(sev_key, "rgba(100, 116, 139, 0.12)")
    border = SEVERITY_BORDER_COLORS.get(sev_key, "rgba(100, 116, 139, 0.28)")

    if custom_label:
        label = custom_label
    else:
        label = SEVERITY_LABELS.get(sev_key, sev_key.upper())

    st.markdown(
        f'<span style="background:{bg};color:{color};border:1px solid {border};'
        f'padding:3px 12px;border-radius:9999px;font-size:12px;font-weight:700;'
        f'letter-spacing:0.04em;display:inline-flex;align-items:center;box-shadow:0 0 12px {bg};">'
        f'{label}</span>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    """Render a coloured status pill badge for a check or contract outcome."""
    stat_key = str(status).lower()
    color = STATUS_COLORS.get(stat_key, COLOR_NEUTRAL)
    bg = STATUS_BG_COLORS.get(stat_key, "rgba(100, 116, 139, 0.12)")
    border = STATUS_BORDER_COLORS.get(stat_key, "rgba(100, 116, 139, 0.25)")
    icon = STATUS_ICONS.get(stat_key, "•")
    label = str(status).upper()

    st.markdown(
        f'<span style="background:{bg};color:{color};border:1px solid {border};'
        f'padding:2px 9px;border-radius:9999px;font-size:11px;font-weight:700;'
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
    """Render a cyan informational callout banner."""
    st.markdown(
        f'<div class="sg-callout sg-callout-info">{message}</div>',
        unsafe_allow_html=True,
    )


def warning_box(message: str) -> None:
    """Render an amber warning callout banner."""
    st.markdown(
        f'<div class="sg-callout sg-callout-warning">{message}</div>',
        unsafe_allow_html=True,
    )


def error_box(message: str) -> None:
    """Render a crimson critical error callout banner."""
    st.markdown(
        f'<div class="sg-callout sg-callout-danger">{message}</div>',
        unsafe_allow_html=True,
    )


def success_box(message: str) -> None:
    """Render an emerald success callout banner."""
    st.markdown(
        f'<div class="sg-callout sg-callout-success">{message}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric & Structure Helpers
# ---------------------------------------------------------------------------

def metric_tile(
    label: str,
    value: str | int | float,
    subtext: str | None = None,
    delta: str | None = None,
) -> None:
    """Render a single Raycast-grade dark glass stat tile."""
    sub_html = f'<div style="font-size:11px;color:#94A3B8;margin-top:4px;">{subtext}</div>' if subtext else ""
    delta_html = f'<span style="font-size:11px;color:#22C55E;margin-left:6px;">{delta}</span>' if delta else ""
    st.markdown(
        f"""
        <div class="sg-stat-tile">
            <span class="sg-stat-label">{label}</span>
            <div style="display:flex;align-items:baseline;">
                <span class="sg-stat-value">{value}</span>
                {delta_html}
            </div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_row(metrics: dict[str, str | int | float]) -> None:
    """Render a horizontal row of glass stat tiles."""
    cols = st.columns(len(metrics))
    for col, (label, val) in zip(cols, metrics.items()):
        with col:
            metric_tile(label, val)


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section heading with subtle border."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown(
        "<div style='height:1px;background:rgba(255,255,255,0.08);margin:0.75rem 0 1.25rem 0;'></div>",
        unsafe_allow_html=True,
    )


def code_snippet(code: str, language: str = "sql") -> None:
    """Display monospaced SQL or code inside a dark editor container."""
    st.markdown(
        f"""
        <div class="sg-code-container">
            <pre style="margin:0;padding:0;background:transparent;border:none;"><code>{code.strip()}</code></pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """Render an elegant Apple / Linear-grade footer."""
    st.markdown(
        """
        <div style="margin-top:4rem;padding-top:1.5rem;border-top:1px solid rgba(255,255,255,0.08);font-size:12px;color:#64748B;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <span style="color:#A5B4FC;font-weight:600;">SchemaGuard</span>
                <span>•</span>
                <span>Local-First SQLite Migration Rehearsal & Compatibility Verification</span>
            </div>
            <div>Never executes against production databases • Sandboxed via SQLite backup API</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
