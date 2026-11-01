"""
ui/components.py
----------------
Reusable Streamlit widget helpers.

Each function wraps one logical UI element so that pages stay declarative and
thin.  Functions accept plain Python values and call ``st.*`` internally —
no Streamlit state is mutated here.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import (
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_INFO,
    SEVERITY_COLORS,
    STATUS_COLORS,
    STATUS_ICONS,
)


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------


def severity_badge(severity: str) -> None:
    """Render a coloured inline badge for a :class:`~schemaguard.models.Severity` value."""
    colour = SEVERITY_COLORS.get(severity.lower(), "#6B7280")
    label = severity.upper()
    st.markdown(
        f'<span style="background:{colour};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:600;">{label}</span>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    """Render a coloured inline badge for a :class:`~schemaguard.models.CheckStatus` value."""
    colour = STATUS_COLORS.get(status.lower(), "#6B7280")
    icon = STATUS_ICONS.get(status.lower(), "")
    label = status.upper()
    st.markdown(
        f'<span style="background:{colour};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:11px;font-weight:600;">{icon} {label}</span>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Callout boxes
# ---------------------------------------------------------------------------


def info_box(message: str) -> None:
    """Render a blue informational callout."""
    st.markdown(
        f'<div style="background:#EFF6FF;border-left:4px solid {COLOR_INFO};'
        f'padding:10px 14px;border-radius:4px;font-size:13px;">{message}</div>',
        unsafe_allow_html=True,
    )


def warning_box(message: str) -> None:
    """Render an amber warning callout."""
    st.markdown(
        f'<div style="background:#FFFBEB;border-left:4px solid {COLOR_WARNING};'
        f'padding:10px 14px;border-radius:4px;font-size:13px;">{message}</div>',
        unsafe_allow_html=True,
    )


def error_box(message: str) -> None:
    """Render a red error callout."""
    st.markdown(
        f'<div style="background:#FEF2F2;border-left:4px solid {COLOR_ERROR};'
        f'padding:10px 14px;border-radius:4px;font-size:13px;">{message}</div>',
        unsafe_allow_html=True,
    )


def success_box(message: str) -> None:
    """Render a green success callout."""
    st.markdown(
        f'<div style="background:#ECFDF5;border-left:4px solid {COLOR_SUCCESS};'
        f'padding:10px 14px;border-radius:4px;font-size:13px;">{message}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------


def section_header(title: str, subtitle: str = "") -> None:
    """Render a consistent section heading with an optional subtitle."""
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()


# ---------------------------------------------------------------------------
# Metric row
# ---------------------------------------------------------------------------


def metric_row(metrics: dict[str, str | int | float]) -> None:
    """Render a horizontal row of ``st.metric`` tiles.

    Args:
        metrics: Mapping of label → value pairs to display.
    """
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label=label, value=str(value))

