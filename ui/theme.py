"""
ui/theme.py
-----------
Central colour palette and typography constants used across all Streamlit pages.

Importing from here (rather than hard-coding hex values inline) means the
entire UI can be restyled by changing values in one place.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------

COLOR_PRIMARY: str = "#4F46E5"      # Indigo-600  — primary actions / headers
COLOR_SECONDARY: str = "#7C3AED"    # Violet-600  — accent / highlights
COLOR_SUCCESS: str = "#059669"      # Emerald-600 — passed checks
COLOR_WARNING: str = "#D97706"      # Amber-600   — warnings
COLOR_ERROR: str = "#DC2626"        # Red-600     — failures / critical
COLOR_INFO: str = "#0284C7"         # Sky-600     — informational badges
COLOR_NEUTRAL: str = "#6B7280"      # Gray-500    — muted text

# ---------------------------------------------------------------------------
# Severity → colour mapping (matches models.Severity)
# ---------------------------------------------------------------------------

SEVERITY_COLORS: dict[str, str] = {
    "critical": COLOR_ERROR,
    "high": COLOR_ERROR,
    "error": COLOR_ERROR,
    "moderate": COLOR_WARNING,
    "warning": COLOR_WARNING,
    "low": COLOR_INFO,
    "info": COLOR_INFO,
}

# ---------------------------------------------------------------------------
# Status → colour mapping (matches models.CheckStatus)
# ---------------------------------------------------------------------------

STATUS_COLORS: dict[str, str] = {
    "passed": COLOR_SUCCESS,
    "failed": COLOR_ERROR,
    "skipped": COLOR_NEUTRAL,
    "error": COLOR_ERROR,
}

STATUS_ICONS: dict[str, str] = {
    "passed": "✅",
    "failed": "❌",
    "skipped": "⏭️",
    "error": "💥",
}

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

FONT_FAMILY: str = "'Inter', 'Segoe UI', sans-serif"
FONT_SIZE_BASE: str = "14px"
FONT_SIZE_SMALL: str = "12px"
FONT_SIZE_HEADING: str = "20px"

