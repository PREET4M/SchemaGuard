"""
backend/main.py
---------------
FastAPI REST API server for SchemaGuard.

Connects the Next.js React frontend directly to the core SQLite rehearsal engine:
  - Source database inspection (read-only)
  - Custom database upload & validation
  - Isolated migration execution in sandbox copies
  - Application query contract verification
  - Invariant assertion checks
  - Structural schema diff & data profiling
  - Evidence report downloads (JSON & Markdown)
"""

from __future__ import annotations

from pathlib import Path
import platform
import sqlite3
import uuid
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
import sqlglot

from schemaguard.config import (
    MAX_SAMPLE_ROWS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    QUERY_TIMEOUT_SECONDS,
    SANDBOX_DB_FILENAME,
    SANDBOX_DIR,
    SANDBOX_PRAGMAS,
)
from schemaguard.core.orchestrator import RehearsalReport, rehearse_migration
from schemaguard.utils.file_validation import FileValidationError, validate_sqlite_file

app = FastAPI(
    title="SchemaGuard API",
    description="Local-first SQLite Migration Rehearsal & Verification Engine API",
    version="2.0.0",
)

# Enable CORS for Next.js frontend (default port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root directory resolution for cross-platform and subfolder robustness
BASE_DIR = Path(__file__).resolve().parent.parent
DEMO_DIR = BASE_DIR / "data" / "demo"
DEMO_DB_PATH = DEMO_DIR / "ecommerce.db"
MIGRATION_DIR = DEMO_DIR / "migrations"
CONTRACTS_DIR = DEMO_DIR / "contracts"
INVARIANTS_DIR = DEMO_DIR / "invariants"
UPLOAD_DIR = BASE_DIR / SANDBOX_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory storage for active reports & uploaded files
REPORT_CACHE: dict[str, RehearsalReport] = {}
UPLOADED_FILES: dict[str, Path] = {}


def _read_file_safe(path: Path) -> str:
    """Read file content safely or return empty string."""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _serialize_report(report: RehearsalReport, rehearsal_id: str) -> dict[str, Any]:
    """Serialize RehearsalReport into a clean JSON dictionary for Next.js."""
    m_res = report.migration_result
    risk = report.risk_assessment
    diff = m_res.schema_diff
    findings = m_res.schema_findings
    contracts = m_res.contract_results
    invariants = m_res.invariant_results
    profile = report.data_profile

    # Contracts serialization
    contracts_data = []
    for c in contracts:
        c_status = str(c.status).upper()
        if hasattr(c.status, "value"):
            c_status = c.status.value.upper()
        contracts_data.append({
            "name": c.name,
            "contract_type": c.contract_type.value if hasattr(c.contract_type, "value") else str(c.contract_type),
            "status": c_status,
            "sql_statement": c.sql_statement,
            "column_names": list(c.column_names) if c.column_names else [],
            "row_count_post": c.row_count_post,
            "execution_time_ms": round(c.execution_time_ms, 2),
            "error_message": c.error_message,
        })

    # Invariants serialization
    invariants_data = []
    for inv in invariants:
        inv_status = str(inv.status).upper()
        if hasattr(inv.status, "value"):
            inv_status = inv.status.value.upper()
        invariants_data.append({
            "name": inv.name,
            "status": inv_status,
            "sql": inv.sql,
            "violating_rows_count": inv.violating_rows_count,
            "sample_violations": list(inv.sample_violations) if inv.sample_violations else [],
            "execution_time_ms": round(inv.execution_time_ms, 2),
            "error_message": inv.error_message,
            "held": inv.held(),
        })

    # Findings / Static warnings serialization
    findings_data = []
    for f in findings:
        f_sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        findings_data.append({
            "rule_id": f.rule_id,
            "severity": f_sev.upper(),
            "title": f.title or f.rule_id,
            "explanation": f.explanation,
            "evidence": f.evidence,
            "statement_index": f.statement_index,
            "human_review_action": f.human_review_action,
        })

    # Schema Diff serialization
    diff_data = {
        "tables_added": list(diff.tables_added),
        "tables_removed": list(diff.tables_removed),
        "tables_modified": list(diff.tables_modified),
        "columns_added": {k: list(v) for k, v in diff.columns_added.items()},
        "columns_removed": {k: list(v) for k, v in diff.columns_removed.items()},
        "columns_modified": {k: {ck: list(cv) for ck, cv in v.items()} for k, v in diff.columns_modified.items()},
        "indexes_added": list(diff.indexes_added),
        "indexes_removed": list(diff.indexes_removed),
        "foreign_keys_added": {k: list(v) for k, v in diff.foreign_keys_added.items()},
        "foreign_keys_removed": {k: list(v) for k, v in diff.foreign_keys_removed.items()},
        "is_clean": diff.is_clean(),
    }

    # Data Profile serialization
    profile_data = []
    if profile and profile.table_deltas:
        for tp in profile.table_deltas.values():
            profile_data.append({
                "table_name": tp.table_name,
                "pre_count": tp.pre_count if tp.pre_count is not None else 0,
                "post_count": tp.post_count if tp.post_count is not None else 0,
                "delta": tp.delta,
                "status": tp.status,
                "is_row_drop": tp.is_row_drop,
            })

    # Risk factors
    risk_factors = []
    if risk and risk.factors:
        for rf in risk.factors:
            risk_factors.append({
                "category": rf.category,
                "points": rf.points,
                "description": rf.description,
            })

    sev_value = report.severity.value if hasattr(report.severity, "value") else str(report.severity)

    return {
        "rehearsal_id": rehearsal_id,
        "severity": sev_value.upper(),
        "label": report.label,
        "succeeded": report.succeeded,
        "post_checks_run": report.post_checks_run,
        "migration_result": {
            "migration_applied": m_res.migration_applied,
            "migration_error": m_res.migration_error,
            "elapsed_total_ms": round(m_res.elapsed_total_ms, 2),
            "migration_sql": m_res.migration_sql,
        },
        "risk_assessment": {
            "overall_severity": sev_value.upper(),
            "risk_score": risk.risk_score if risk else 0,
            "summary_label": report.label,
            "factors": risk_factors,
        },
        "schema_diff": diff_data,
        "contract_results": contracts_data,
        "invariant_results": invariants_data,
        "data_profile": profile_data,
        "schema_findings": findings_data,
        "timestamp": report.migration_result.run_timestamp_utc,
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": "SchemaGuard",
        "version": "2.0.0",
        "sqlite_version": sqlite3.sqlite_version,
        "python_version": platform.python_version(),
    }


@app.get("/api/demo/metadata")
def get_demo_metadata() -> dict[str, Any]:
    """Retrieve demo database metadata, available tables, presets, contracts, and invariants."""
    if not DEMO_DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Demo database file not found. Run scripts/create_demo_db.py.")

    # Inspect demo database tables safely in read-only mode
    tables_info = []
    try:
        conn = sqlite3.connect(f"file:{DEMO_DB_PATH.resolve()}?mode=ro", uri=True)
        cur = conn.cursor()
        tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for t in tables:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            tables_info.append({"name": t, "row_count": cnt})
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect demo database: {e}")

    # Read default presets
    preset_safe = _read_file_safe(MIGRATION_DIR / "01_safe_add_column.sql")
    preset_break = _read_file_safe(MIGRATION_DIR / "02_break_old_query.sql")
    preset_drop = _read_file_safe(MIGRATION_DIR / "03_drop_table.sql")
    old_contracts = _read_file_safe(CONTRACTS_DIR / "old_app.sql")
    new_contracts = _read_file_safe(CONTRACTS_DIR / "new_app.sql")
    invariants = _read_file_safe(INVARIANTS_DIR / "invariants.sql")

    return {
        "database_name": "ecommerce.db",
        "database_path": str(DEMO_DB_PATH.resolve()),
        "tables": tables_info,
        "scenarios": {
            "safe": {
                "key": "safe",
                "name": "Safe Column Addition",
                "filename": "01_safe_add_column.sql",
                "severity": "LOW",
                "description": "Appends phone TEXT to users table. Both old and new application contracts pass cleanly.",
                "migration_sql": preset_safe,
            },
            "break_contract": {
                "key": "break_contract",
                "name": "Breaking Query Contract",
                "filename": "02_break_old_query.sql",
                "severity": "CRITICAL",
                "description": "Drops email from users. Triggers an immediate CRITICAL failure on the active application query contract.",
                "migration_sql": preset_break,
            },
            "drop_table": {
                "key": "drop_table",
                "name": "Destructive Table Drop",
                "filename": "03_drop_table.sql",
                "severity": "HIGH",
                "description": "Drops order_items table. Triggers AST static warnings and schema removal alerts.",
                "migration_sql": preset_drop,
            },
        },
        "default_contracts": {
            "old_app_sql": old_contracts,
            "new_app_sql": new_contracts,
        },
        "default_invariants_sql": invariants,
    }


@app.post("/api/upload-database")
@app.post("/api/upload-db")
async def upload_database(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept and validate custom SQLite database upload."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name.")

    # Read content
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum permitted limit of {MAX_UPLOAD_SIZE_MB} MB."
        )

    upload_id = str(uuid.uuid4())
    saved_filename = f"{upload_id}_{file.filename}"
    saved_path = UPLOAD_DIR / saved_filename
    saved_path.write_bytes(contents)

    # Validate file integrity as a real SQLite database
    try:
        validate_sqlite_file(saved_path, max_size_bytes=MAX_UPLOAD_SIZE_BYTES)
    except FileValidationError as e:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid SQLite database: {e}")

    # Inspect tables in the uploaded database
    tables_info = []
    try:
        conn = sqlite3.connect(f"file:{saved_path.resolve()}?mode=ro", uri=True)
        cur = conn.cursor()
        tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for t in tables:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            tables_info.append({"name": t, "row_count": cnt})
        conn.close()
    except Exception as e:
        tables_info = []

    UPLOADED_FILES[upload_id] = saved_path

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "size_bytes": len(contents),
        "tables": tables_info,
        "message": f"Successfully validated and uploaded {file.filename}.",
    }


class RehearsalRequest(BaseModel):
    source_type: str = Field(default="demo", description="'demo' or 'upload'")
    upload_id: str | None = Field(default=None, description="Upload identifier if source_type == 'upload'")
    migration_sql: str = Field(..., description="Migration SQL DDL statements")
    old_app_contracts: list[str] = Field(default_factory=list, description="Production query contracts")
    new_app_contracts: list[str] = Field(default_factory=list, description="Upcoming query contracts")
    invariants: list[str] = Field(default_factory=list, description="Zero-row data invariant queries")


@app.post("/api/rehearse")
def execute_rehearsal(req: RehearsalRequest) -> dict[str, Any]:
    """Execute isolated migration rehearsal against a disposable sandbox clone."""
    # Resolve source database
    if req.source_type == "upload":
        if not req.upload_id or req.upload_id not in UPLOADED_FILES:
            raise HTTPException(status_code=400, detail="Invalid or expired upload ID. Please upload your database again.")
        source_db_path = UPLOADED_FILES[req.upload_id]
        if not source_db_path.exists():
            raise HTTPException(status_code=400, detail="Uploaded database file no longer exists.")
    else:
        if not DEMO_DB_PATH.exists():
            raise HTTPException(status_code=404, detail="Demo database file not found. Run scripts/create_demo_db.py.")
        source_db_path = DEMO_DB_PATH

    if not req.migration_sql.strip():
        raise HTTPException(status_code=400, detail="Migration SQL cannot be empty.")

    try:
        report = rehearse_migration(
            source_db_path=source_db_path,
            migration_sql=req.migration_sql,
            old_app_contracts=req.old_app_contracts,
            new_app_contracts=req.new_app_contracts,
            invariants=req.invariants,
            max_file_size_mb=MAX_UPLOAD_SIZE_MB,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rehearsal execution error: {e}")

    rehearsal_id = str(uuid.uuid4())
    REPORT_CACHE[rehearsal_id] = report

    return _serialize_report(report, rehearsal_id)


@app.get("/api/rehearsals/{rehearsal_id}")
def get_rehearsal(rehearsal_id: str) -> dict[str, Any]:
    """Retrieve previously executed rehearsal results."""
    report = REPORT_CACHE.get(rehearsal_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rehearsal report not found or expired.")
    return _serialize_report(report, rehearsal_id)


@app.get("/api/rehearsals/{rehearsal_id}/markdown")
def download_markdown(rehearsal_id: str) -> PlainTextResponse:
    """Download Markdown audit report."""
    report = REPORT_CACHE.get(rehearsal_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rehearsal report not found.")
    md_content = report.to_markdown()
    return PlainTextResponse(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=schemaguard_report_{rehearsal_id[:8]}.md"}
    )


@app.get("/api/rehearsals/{rehearsal_id}/json")
def download_json(rehearsal_id: str) -> PlainTextResponse:
    """Download JSON audit report."""
    report = REPORT_CACHE.get(rehearsal_id)
    if not report:
        raise HTTPException(status_code=404, detail="Rehearsal report not found.")
    json_content = report.to_json(indent=2)
    return PlainTextResponse(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=schemaguard_report_{rehearsal_id[:8]}.json"}
    )


@app.get("/api/settings")
def get_settings() -> dict[str, Any]:
    """Retrieve execution constraints, connection pragmas, and authorizer rules."""
    return {
        "constraints": {
            "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
            "statement_timeout_seconds": QUERY_TIMEOUT_SECONDS,
            "max_sample_rows": MAX_SAMPLE_ROWS,
            "sandbox_directory": str(SANDBOX_DIR),
            "sandbox_clone_filename": SANDBOX_DB_FILENAME,
        },
        "pragmas": SANDBOX_PRAGMAS,
        "authorizer_rules": [
            "SQLITE_ATTACH / DETACH blocked from referencing external databases",
            "PRAGMA writable_schema blocked to prevent catalog corruption",
            "sqlite3_enable_load_extension blocked to reject unvetted native binaries",
            "Mutation operations (INSERT, UPDATE, DELETE, DDL) strictly blocked during contract replays",
        ],
        "runtime": {
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "sqlglot_version": sqlglot.__version__,
            "platform": platform.platform(),
        },
    }
