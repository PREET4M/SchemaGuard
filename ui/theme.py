"""
ui/theme.py
-----------
Central colour palette, typography constants, and status mappings
used across all Streamlit pages in SchemaGuard.

Design Philosophy:
  - Clean, restrained developer interface.
  - Off-white warm background, dark typography, subtle borders.
  - Distinct status tags and severity indicators.
  - Strict absence of misleading claims: LOW severity is labeled
    "No configured checks failed", never "guaranteed safe".
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Background & Surface Tokens
# ---------------------------------------------------------------------------

COLOR_BG: str = "#F8F9FA"                   # Off-white warm background
COLOR_SURFACE: str = "#FFFFFF"              # Pure white card surface
COLOR_SURFACE_TRANSLUCENT: str = "rgba(255, 255, 255, 0.92)"
COLOR_CARD_BORDER: str = "#E2E8F0"          # Slate-200 border
COLOR_BORDER_SUBTLE: str = "#F1F5F9"        # Slate-100 divider

# ---------------------------------------------------------------------------
# Typography Tokens
# ---------------------------------------------------------------------------

COLOR_TEXT_PRIMARY: str = "#0F172A"        # Slate-900 — headings and primary text
COLOR_TEXT_SECONDARY: str = "#334155"      # Slate-700 — body text
COLOR_TEXT_MUTED: str = "#64748B"          # Slate-500 — captions and labels

# ---------------------------------------------------------------------------
# Brand & Accent Colours
# ---------------------------------------------------------------------------

COLOR_PRIMARY: str = "#2563EB"             # Blue-600 — primary actions / focal points
COLOR_PRIMARY_DARK: str = "#1D4ED8"        # Blue-700
COLOR_PRIMARY_LIGHT: str = "#EFF6FF"       # Blue-50
COLOR_SECONDARY: str = "#4F46E5"           # Indigo-600 — secondary accent

COLOR_SUCCESS: str = "#059669"             # Emerald-600 — passed checks / zero violations
COLOR_SUCCESS_BG: str = "#ECFDF5"
COLOR_SUCCESS_BORDER: str = "#A7F3D0"

COLOR_WARNING: str = "#D97706"             # Amber-600 — warnings / moderate risk
COLOR_WARNING_BG: str = "#FFFBEB"
COLOR_WARNING_BORDER: str = "#FDE68A"

COLOR_ERROR: str = "#DC2626"               # Red-600 — critical / failures
COLOR_ERROR_BG: str = "#FEF2F2"
COLOR_ERROR_BORDER: str = "#FECACA"

COLOR_INFO: str = "#0284C7"                # Sky-600 — informational badges
COLOR_INFO_BG: str = "#F0F9FF"
COLOR_INFO_BORDER: str = "#BAE6FD"

COLOR_NEUTRAL: str = "#6B7280"             # Gray-500 — muted badges
COLOR_NEUTRAL_BG: str = "#F3F4F6"
COLOR_NEUTRAL_BORDER: str = "#E5E7EB"

# ---------------------------------------------------------------------------
# Severity Mappings (matches models.Severity)
# ---------------------------------------------------------------------------

SEVERITY_COLORS: dict[str, str] = {
    "critical": COLOR_ERROR,
    "high": "#BE123C",                     # Rose-700
    "error": COLOR_ERROR,
    "moderate": COLOR_WARNING,
    "warning": COLOR_WARNING,
    "low": COLOR_SUCCESS,
    "info": COLOR_INFO,
}

SEVERITY_BG_COLORS: dict[str, str] = {
    "critical": COLOR_ERROR_BG,
    "high": "#FFF1F2",
    "error": COLOR_ERROR_BG,
    "moderate": COLOR_WARNING_BG,
    "warning": COLOR_WARNING_BG,
    "low": COLOR_SUCCESS_BG,
    "info": COLOR_INFO_BG,
}

SEVERITY_BORDER_COLORS: dict[str, str] = {
    "critical": COLOR_ERROR_BORDER,
    "high": "#FECDD3",
    "error": COLOR_ERROR_BORDER,
    "moderate": COLOR_WARNING_BORDER,
    "warning": COLOR_WARNING_BORDER,
    "low": COLOR_SUCCESS_BORDER,
    "info": COLOR_INFO_BORDER,
}

# Explicit labels required by product specification
SEVERITY_LABELS: dict[str, str] = {
    "critical": "CRITICAL RISK",
    "high": "HIGH RISK",
    "moderate": "MODERATE RISK",
    "low": "No configured checks failed",
    "info": "INFORMATIONAL",
}

# ---------------------------------------------------------------------------
# Status Mappings (matches models.CheckStatus / ContractStatus / InvariantStatus)
# ---------------------------------------------------------------------------

STATUS_COLORS: dict[str, str] = {
    "passed": COLOR_SUCCESS,
    "pass": COLOR_SUCCESS,
    "failed": COLOR_ERROR,
    "fail": COLOR_ERROR,
    "error": COLOR_ERROR,
    "skipped": COLOR_NEUTRAL,
    "rejected": COLOR_WARNING,
}

STATUS_BG_COLORS: dict[str, str] = {
    "passed": COLOR_SUCCESS_BG,
    "pass": COLOR_SUCCESS_BG,
    "failed": COLOR_ERROR_BG,
    "fail": COLOR_ERROR_BG,
    "error": COLOR_ERROR_BG,
    "skipped": COLOR_NEUTRAL_BG,
    "rejected": COLOR_WARNING_BG,
}

STATUS_BORDER_COLORS: dict[str, str] = {
    "passed": COLOR_SUCCESS_BORDER,
    "pass": COLOR_SUCCESS_BORDER,
    "failed": COLOR_ERROR_BORDER,
    "fail": COLOR_ERROR_BORDER,
    "error": COLOR_ERROR_BORDER,
    "skipped": COLOR_NEUTRAL_BORDER,
    "rejected": COLOR_WARNING_BORDER,
}

STATUS_ICONS: dict[str, str] = {
    "passed": "✓",
    "pass": "✓",
    "failed": "✗",
    "fail": "✗",
    "skipped": "⊘",
    "error": "!",
    "rejected": "⊘",
}

# ---------------------------------------------------------------------------
# Typography Tokens
# ---------------------------------------------------------------------------

FONT_FAMILY_SANS: str = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
)
FONT_FAMILY_MONO: str = (
    "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
)

FONT_SIZE_BASE: str = "14px"
FONT_SIZE_SMALL: str = "12px"
FONT_SIZE_HEADING: str = "20px"
