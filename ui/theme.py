"""
ui/theme.py
-----------
Central visual design system, color tokens, and semantic mappings for SchemaGuard.

Inspired by the design quality of Apple.com, Linear, and Raycast:
  - Deep atmospheric dark palette (#090A0F, #0D111A, #121722)
  - Refined translucent glass surfaces with backdrop blur
  - Vibrant Indigo-Cyan accent gradients
  - Strict semantic severity indicators (LOW is always labeled
    "No configured checks failed", never claiming "guaranteed safe")
  - SF Pro / Inter typography tokens with tabular numerals
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Background & Atmospheric Canvas Tokens
# ---------------------------------------------------------------------------

COLOR_BG_DARKEST: str = "#090A0F"          # Deepest void background
COLOR_BG: str = "#0D111A"                  # Primary application canvas
COLOR_BG_ELEVATED: str = "#121722"         # Elevated sections & modules

# ---------------------------------------------------------------------------
# Glassmorphism & Surface Tokens
# ---------------------------------------------------------------------------

COLOR_SURFACE_GLASS: str = "rgba(22, 27, 38, 0.70)"      # Primary card glass
COLOR_SURFACE_GLASS_HOVER: str = "rgba(30, 36, 50, 0.80)"# Hover glass elevation
COLOR_SURFACE_GLASS_ACTIVE: str = "rgba(38, 46, 64, 0.85)"
COLOR_SURFACE_SOLID: str = "#161B26"                     # Non-translucent fallback

COLOR_BORDER_GLASS: str = "rgba(255, 255, 255, 0.08)"     # Subtle white border
COLOR_BORDER_GLASS_HOVER: str = "rgba(255, 255, 255, 0.16)"
COLOR_BORDER_SUBTLE: str = "rgba(255, 255, 255, 0.05)"

# ---------------------------------------------------------------------------
# Typography Tokens
# ---------------------------------------------------------------------------

COLOR_TEXT_PRIMARY: str = "#F8FAFC"        # Slate-50 — High-contrast text & titles
COLOR_TEXT_SECONDARY: str = "#94A3B8"      # Slate-400 — Supporting body copy
COLOR_TEXT_MUTED: str = "#64748B"          # Slate-500 — Captions, labels & timestamps

# ---------------------------------------------------------------------------
# Brand & Accent Tokens (Indigo to Cyan)
# ---------------------------------------------------------------------------

COLOR_ACCENT_INDIGO: str = "#6366F1"       # Primary brand accent
COLOR_ACCENT_CYAN: str = "#06B6D4"         # Secondary vibrant accent
COLOR_ACCENT_BLUE: str = "#3B82F6"         # Tertiary technical accent

GRADIENT_PRIMARY: str = "linear-gradient(135deg, #6366F1 0%, #3B82F6 50%, #06B6D4 100%)"
GRADIENT_HERO_TEXT: str = "linear-gradient(180deg, #FFFFFF 0%, #CBD5E1 100%)"
GRADIENT_GLASS_CARD: str = "linear-gradient(145deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%)"

# Backward-compatibility aliases
COLOR_PRIMARY: str = "#6366F1"
COLOR_SECONDARY: str = "#06B6D4"
COLOR_INFO: str = "#06B6D4"
COLOR_INFO_BG: str = "rgba(6, 182, 212, 0.12)"
COLOR_INFO_BORDER: str = "rgba(6, 182, 212, 0.28)"

# ---------------------------------------------------------------------------
# Semantic Colours (Apple / Linear Grade)
# ---------------------------------------------------------------------------

COLOR_CRITICAL: str = "#EF4444"            # Red-500
COLOR_CRITICAL_BG: str = "rgba(239, 68, 68, 0.12)"
COLOR_CRITICAL_BORDER: str = "rgba(239, 68, 68, 0.30)"

COLOR_HIGH: str = "#F97316"                # Orange-500
COLOR_HIGH_BG: str = "rgba(249, 115, 22, 0.12)"
COLOR_HIGH_BORDER: str = "rgba(249, 115, 22, 0.30)"

COLOR_MODERATE: str = "#EAB308"            # Yellow-500
COLOR_MODERATE_BG: str = "rgba(234, 179, 8, 0.12)"
COLOR_MODERATE_BORDER: str = "rgba(234, 179, 8, 0.30)"

COLOR_LOW: str = "#22C55E"                 # Green-500
COLOR_LOW_BG: str = "rgba(34, 197, 94, 0.12)"
COLOR_LOW_BORDER: str = "rgba(34, 197, 94, 0.30)"

# Backward-compatibility aliases for existing test suites
COLOR_SUCCESS: str = COLOR_LOW
COLOR_SUCCESS_BG: str = COLOR_LOW_BG
COLOR_SUCCESS_BORDER: str = COLOR_LOW_BORDER

COLOR_WARNING: str = COLOR_MODERATE
COLOR_WARNING_BG: str = COLOR_MODERATE_BG
COLOR_WARNING_BORDER: str = COLOR_MODERATE_BORDER

COLOR_ERROR: str = COLOR_CRITICAL
COLOR_ERROR_BG: str = COLOR_CRITICAL_BG
COLOR_ERROR_BORDER: str = COLOR_CRITICAL_BORDER

COLOR_NEUTRAL: str = "#64748B"
COLOR_NEUTRAL_BG: str = "rgba(100, 116, 139, 0.12)"
COLOR_NEUTRAL_BORDER: str = "rgba(100, 116, 139, 0.25)"

# ---------------------------------------------------------------------------
# Severity Mappings (matches models.Severity)
# ---------------------------------------------------------------------------

SEVERITY_COLORS: dict[str, str] = {
    "critical": COLOR_CRITICAL,
    "high": COLOR_HIGH,
    "error": COLOR_CRITICAL,
    "moderate": COLOR_MODERATE,
    "warning": COLOR_MODERATE,
    "low": COLOR_LOW,
    "info": COLOR_INFO,
}

SEVERITY_BG_COLORS: dict[str, str] = {
    "critical": COLOR_CRITICAL_BG,
    "high": COLOR_HIGH_BG,
    "error": COLOR_CRITICAL_BG,
    "moderate": COLOR_MODERATE_BG,
    "warning": COLOR_MODERATE_BG,
    "low": COLOR_LOW_BG,
    "info": COLOR_INFO_BG,
}

SEVERITY_BORDER_COLORS: dict[str, str] = {
    "critical": COLOR_CRITICAL_BORDER,
    "high": COLOR_HIGH_BORDER,
    "error": COLOR_CRITICAL_BORDER,
    "moderate": COLOR_MODERATE_BORDER,
    "warning": COLOR_MODERATE_BORDER,
    "low": COLOR_LOW_BORDER,
    "info": COLOR_INFO_BORDER,
}

# Strict product mandate: LOW severity is ALWAYS labeled "No configured checks failed"
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
    "passed": COLOR_LOW,
    "pass": COLOR_LOW,
    "failed": COLOR_CRITICAL,
    "fail": COLOR_CRITICAL,
    "error": COLOR_CRITICAL,
    "skipped": COLOR_NEUTRAL,
    "rejected": COLOR_MODERATE,
}

STATUS_BG_COLORS: dict[str, str] = {
    "passed": COLOR_LOW_BG,
    "pass": COLOR_LOW_BG,
    "failed": COLOR_CRITICAL_BG,
    "fail": COLOR_CRITICAL_BG,
    "error": COLOR_CRITICAL_BG,
    "skipped": COLOR_NEUTRAL_BG,
    "rejected": COLOR_MODERATE_BG,
}

STATUS_BORDER_COLORS: dict[str, str] = {
    "passed": COLOR_LOW_BORDER,
    "pass": COLOR_LOW_BORDER,
    "failed": COLOR_CRITICAL_BORDER,
    "fail": COLOR_CRITICAL_BORDER,
    "error": COLOR_CRITICAL_BORDER,
    "skipped": COLOR_NEUTRAL_BORDER,
    "rejected": COLOR_MODERATE_BORDER,
}

STATUS_ICONS: dict[str, str] = {
    "passed": "✓",
    "pass": "✓",
    "failed": "✕",
    "fail": "✕",
    "skipped": "⊘",
    "error": "!",
    "rejected": "⊘",
}

# ---------------------------------------------------------------------------
# Typography Tokens
# ---------------------------------------------------------------------------

FONT_FAMILY_SANS: str = (
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)
FONT_FAMILY_MONO: str = (
    "'SF Mono', ui-monospace, Menlo, Monaco, Consolas, 'Liberation Mono', monospace"
)

FONT_SIZE_BASE: str = "14px"
FONT_SIZE_SMALL: str = "12px"
FONT_SIZE_HEADING: str = "22px"
