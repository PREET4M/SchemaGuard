"""
tests/test_api.py
-----------------
Unit and integration tests for FastAPI backend endpoints.
"""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app, DEMO_DB_PATH

client = TestClient(app)


def test_health() -> None:
    """Verify health check endpoint returns 200 and version info."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "SchemaGuard"
    assert "version" in data


def test_demo_metadata() -> None:
    """Verify demo metadata endpoint returns table counts, scenarios, and presets."""
    response = client.get("/api/demo/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["database_name"] == "ecommerce.db"
    assert len(data["tables"]) >= 4
    table_names = [t["name"] for t in data["tables"]]
    assert "users" in table_names
    assert "products" in table_names
    assert "orders" in table_names
    assert "order_items" in table_names

    # Check scenarios
    scenarios = data["scenarios"]
    assert "safe" in scenarios
    assert "break_contract" in scenarios
    assert "drop_table" in scenarios


def test_rehearse_safe_scenario() -> None:
    """Verify safe column addition returns LOW severity and succeeds."""
    payload = {
        "source_type": "demo",
        "migration_sql": "ALTER TABLE users ADD COLUMN phone TEXT;",
        "old_app_contracts": ["SELECT id, name, email FROM users WHERE id = 1;"],
        "new_app_contracts": ["SELECT id, name, phone FROM users WHERE id = 1;"],
        "invariants": ["SELECT id FROM users WHERE id < 0;"],
    }
    response = client.post("/api/rehearse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["succeeded"] is True
    assert data["severity"] == "LOW"
    assert data["label"] == "No configured checks failed"
    assert "rehearsal_id" in data
    assert len(data["contract_results"]) == 2
    assert len(data["invariant_results"]) == 1


def test_rehearse_breaking_scenario() -> None:
    """Verify breaking query contract triggers CRITICAL risk."""
    payload = {
        "source_type": "demo",
        "migration_sql": "ALTER TABLE users DROP COLUMN email;",
        "old_app_contracts": ["SELECT id, name, email FROM users WHERE id = 1;"],
        "new_app_contracts": [],
        "invariants": [],
    }
    response = client.post("/api/rehearse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["succeeded"] is False
    assert data["severity"] == "CRITICAL"


def test_rehearse_empty_sql_rejected() -> None:
    """Verify empty migration SQL is rejected with 400 Bad Request."""
    payload = {
        "source_type": "demo",
        "migration_sql": "   ",
    }
    response = client.post("/api/rehearse", json=payload)
    assert response.status_code == 400


def test_downloads() -> None:
    """Verify markdown and JSON downloads for an executed rehearsal."""
    # First rehearse
    rehearse_resp = client.post(
        "/api/rehearse",
        json={
            "source_type": "demo",
            "migration_sql": "ALTER TABLE users ADD COLUMN age INTEGER;",
        },
    )
    assert rehearse_resp.status_code == 200
    rehearsal_id = rehearse_resp.json()["rehearsal_id"]

    # Markdown download
    md_resp = client.get(f"/api/rehearsals/{rehearsal_id}/markdown")
    assert md_resp.status_code == 200
    assert "Migration Rehearsal Report" in md_resp.text

    # JSON download
    json_resp = client.get(f"/api/rehearsals/{rehearsal_id}/json")
    assert json_resp.status_code == 200
    assert '"tool": "SchemaGuard"' in json_resp.text


def test_settings() -> None:
    """Verify settings endpoint returns limits and authorizer rules."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "constraints" in data
    assert "pragmas" in data
    assert "authorizer_rules" in data
    assert "runtime" in data
