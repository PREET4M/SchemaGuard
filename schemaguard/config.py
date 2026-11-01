"""
schemaguard/config.py
---------------------
Project-wide constants and configuration values.

All values are intentionally plain Python (no .env, no secrets) so that
the tool remains purely local-first and reproducible across machines.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB: int = 25
"""Maximum size (in megabytes) accepted for an uploaded SQLite database file."""

MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------

SANDBOX_DIR: str = "temp_sandbox"
"""Root directory where isolated database copies are written during rehearsal.
Excluded from version control via .gitignore."""

SANDBOX_DB_FILENAME: str = "rehearsal_copy.db"
"""Filename given to the sandboxed copy of the source database."""

# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

REPORTS_OUTPUT_DIR: str = "reports_output"
"""Directory where generated HTML / JSON evidence reports are saved."""

REPORT_FILENAME_PREFIX: str = "schemaguard_report"
"""Prefix for report filenames; a timestamp suffix is appended at runtime."""

# ---------------------------------------------------------------------------
# SQL execution
# ---------------------------------------------------------------------------

QUERY_TIMEOUT_SECONDS: int = 30
"""Hard timeout (seconds) applied to every SQL statement executed in the sandbox."""

MAX_SAMPLE_ROWS: int = 500
"""Maximum number of rows returned when sampling a table for diff comparison."""

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

APP_TITLE: str = "SchemaGuard — Migration Rehearsal Engine"
APP_ICON: str = "🛡️"
APP_LAYOUT: str = "wide"

# ---------------------------------------------------------------------------
# SQLite pragmas applied to every sandbox connection
# ---------------------------------------------------------------------------

SANDBOX_PRAGMAS: dict[str, str | int] = {
    "journal_mode": "WAL",
    "foreign_keys": 1,
    "busy_timeout": QUERY_TIMEOUT_SECONDS * 1000,  # milliseconds
}
"""Pragmas applied to the sandbox connection immediately after it is opened."""

