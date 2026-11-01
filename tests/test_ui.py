"""
tests/test_ui.py
----------------
Unit and functional tests for SchemaGuard's Streamlit UI layer:
  - Theme definitions and severity/status mappings
  - Components and badges
  - Query splitting and demo file readers
  - Page render routines with and without active RehearsalReports
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from schemaguard.core.orchestrator import RehearsalReport, rehearse_migration
from schemaguard.models import (
    CheckStatus,
    ContractResult,
    ContractType,
    InvariantResult,
    MigrationResult,
    SchemaDiffResult,
    SchemaFinding,
    Severity,
)
from ui.components import (
    code_snippet,
    diff_badge,
    error_box,
    info_box,
    metric_row,
    metric_tile,
    render_footer,
    render_header,
    section_header,
    severity_badge,
    status_badge,
    success_box,
    warning_box,
)
from ui.pages.overview import _read_file_safe, load_scenario, render_overview_page
from ui.pages.rehearsal import _split_queries, render_rehearsal_page
from ui.pages.results import render_results_page
from ui.pages.settings import render_settings_page
from ui.theme import (
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    SEVERITY_COLORS,
    SEVERITY_LABELS,
    STATUS_COLORS,
    STATUS_ICONS,
)


def test_theme_mappings() -> None:
    """Verify that theme constants strictly enforce product design standards."""
    assert "critical" in SEVERITY_COLORS
    assert "high" in SEVERITY_COLORS
    assert "moderate" in SEVERITY_COLORS
    assert "low" in SEVERITY_COLORS

    # Exact product requirement: LOW severity must never say 'guaranteed safe'
    assert SEVERITY_LABELS["low"] == "No configured checks failed"
    assert "guaranteed safe" not in SEVERITY_LABELS["low"].lower()

    # Check status colors
    assert "pass" in STATUS_COLORS
    assert "fail" in STATUS_COLORS
    assert STATUS_COLORS["pass"] == COLOR_SUCCESS
    assert STATUS_COLORS["fail"] == COLOR_ERROR


def test_diff_badge() -> None:
    """Verify diff badge markup generation for added, removed, and modified."""
    added_badge = diff_badge("ADDED")
    assert "+ ADDED" in added_badge
    assert "sg-diff-add" in added_badge

    removed_badge = diff_badge("REMOVED")
    assert "- REMOVED" in removed_badge
    assert "sg-diff-remove" in removed_badge

    modified_badge = diff_badge("MODIFIED")
    assert "~ MODIFIED" in modified_badge
    assert "sg-diff-modify" in modified_badge


def test_split_queries() -> None:
    """Verify robust query splitting across semicolons, comments, and empty lines."""
    raw_sql = """
    -- Query 1
    SELECT id, name FROM users;

    -- Query 2
    SELECT * FROM orders
    WHERE total > 100;
    """
    queries = _split_queries(raw_sql)
    assert len(queries) == 2
    assert "SELECT id, name FROM users" in queries[0]
    assert "SELECT * FROM orders" in queries[1]


def test_read_file_safe(tmp_path: Path) -> None:
    """Verify safe file reading returns stripped text or empty on missing file."""
    test_file = tmp_path / "sample.sql"
    test_file.write_text("  SELECT 1;  ", encoding="utf-8")
    assert _read_file_safe(test_file) == "SELECT 1;"

    non_existent = tmp_path / "missing.sql"
    assert _read_file_safe(non_existent) == ""


@patch("streamlit.rerun")
def test_load_scenario(mock_rerun: MagicMock) -> None:
    """Verify load_scenario populates session state correctly."""
    session_state: dict[str, any] = {}
    with patch("streamlit.session_state", session_state):
        load_scenario("safe")
        assert session_state.get("db_source_type") == "demo"
        assert session_state.get("demo_loaded") is True
        assert session_state.get("active_page") == "Rehearsal"
        assert "users" in session_state.get("migration_sql", "")

        load_scenario("break_contract")
        assert "DROP COLUMN email" in session_state.get("migration_sql", "")

        load_scenario("drop_table")
        assert "DROP TABLE order_items" in session_state.get("migration_sql", "")


def test_components_render_without_exceptions() -> None:
    """Verify component helper functions execute without raising errors."""
    with patch("streamlit.markdown") as mock_md, patch("streamlit.code") as mock_code:
        render_header()
        assert mock_md.called

        severity_badge("critical")
        severity_badge("low")
        status_badge("PASS")
        status_badge("FAIL")

        info_box("Informational notice")
        warning_box("Warning notice")
        error_box("Error notice")
        success_box("Success notice")

        section_header("Section Title", "Section Subtitle")
        code_snippet("SELECT * FROM users;", language="sql")
        render_footer()


def test_results_page_empty_state() -> None:
    """Verify Results page renders friendly empty-state when no report is present."""
    session_state: dict[str, any] = {}
    with patch("streamlit.session_state", session_state), patch("streamlit.markdown") as mock_md:
        render_results_page()
        assert mock_md.called


def test_results_page_with_active_report(simple_db: Path) -> None:
    """Verify Results page renders all sections when a valid RehearsalReport is present."""
    # Execute a real rehearsal against the simple database
    report = rehearse_migration(
        source_db_path=simple_db,
        migration_sql="ALTER TABLE users ADD COLUMN phone TEXT;",
        old_app_contracts=["SELECT id, name, email FROM users WHERE id = 1;"],
        new_app_contracts=["SELECT id, name, phone FROM users WHERE id = 1;"],
        invariants=["SELECT id FROM users WHERE id < 0;"],
    )

    session_state: dict[str, any] = {"rehearsal_report": report}
    with patch("streamlit.session_state", session_state), patch("streamlit.markdown") as mock_md:
        render_results_page()
        assert mock_md.called
        assert report.succeeded is True
        assert report.severity == Severity.LOW
        assert report.label == "No configured checks failed"


def test_settings_page_render() -> None:
    """Verify Settings page renders constraints and boundaries without error."""
    with patch("streamlit.markdown") as mock_md:
        render_settings_page()
        assert mock_md.called
