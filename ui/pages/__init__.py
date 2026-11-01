"""
ui/pages
--------
SchemaGuard Streamlit page modules:
  - overview: Welcome, product architecture, and 1-click scenario loader.
  - rehearsal: Database source, migration DDL, query contracts, and invariant execution.
  - results: Deterministic findings, contract replays, schema diffs, and report downloads.
  - settings: Sandbox constraints, SQLite pragmas, and authorizer boundaries.
"""

from __future__ import annotations

from ui.pages.overview import render_overview_page
from ui.pages.rehearsal import render_rehearsal_page
from ui.pages.results import render_results_page
from ui.pages.settings import render_settings_page

__all__ = [
    "render_overview_page",
    "render_rehearsal_page",
    "render_results_page",
    "render_settings_page",
]
