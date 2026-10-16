"""FastAPI backend for importing review candidates and logging verified events."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "runs" / "backend" / "events.sqlite3"


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    _init_db(connection)
    return connection


def _init_db(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            video_filename TEXT,
            candidate_type TEXT,
            review_status TEXT,
            payload_json TEXT NOT NULL,
            verified_at TEXT,
            chain_tx_hash TEXT,
            chain_latency_seconds REAL
        )
        """
    )
    connection.commit()


class ImportRequest(BaseModel):
    jsonl_path: str = Field(..., description="Absolute or project-relative JSONL path")


class VerifyRequest(BaseModel):
    reviewer_note: str = ""


class ChainLogRequest(BaseModel):
    evidence_hash_hex: str = Field(..., min_length=64, max_length=64)
    plate_hash_hex: str = Field(..., min_length=64, max_length=64)
    timestamp_utc: int | None = None


app = FastAPI(title="Smart Traffic Violation Review API", version="0.1.0")
DB_PATH = Path(os.environ.get("STVD_DB_PATH", str(DEFAULT_DB)))


@app.on_event("startup")
def startup() -> None:
    with _connect(DB_PATH) as connection:
        _init_db(connection)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events/import")
def import_jsonl(body: ImportRequest) -> dict[str, Any]:
    jsonl_path = Path(body.jsonl_path)
    if not jsonl_path.is_file():
        jsonl_path = PROJECT_ROOT / body.jsonl_path
    if not jsonl_path.is_file():
        raise HTTPException(status_code=404, detail=f"JSONL not found: {body.jsonl_path}")

    imported = 0
    with _connect(DB_PATH) as connection, jsonl_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            event_id = event.get("event_id")
            if not event_id:
                continue
            connection.execute(
                """
                INSERT OR REPLACE INTO events
                (event_id, video_filename, candidate_type, review_status, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event.get("video_filename"),
                    event.get("candidate_type"),
                    event.get("review_status", "NEEDS_REVIEW"),
                    json.dumps(event, ensure_ascii=False),
                ),
            )
            imported += 1
        connection.commit()
    return {"imported": imported, "database": str(DB_PATH.resolve())}


@app.get("/events")
def list_events(status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT event_id, video_filename, candidate_type, review_status, verified_at, chain_tx_hash FROM events"
    params: tuple[Any, ...] = ()
    if status:
        query += " WHERE review_status = ?"
        params = (status,)
    query += " ORDER BY event_id"
    with _connect(DB_PATH) as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.post("/events/{event_id}/verify")
def verify_event(event_id: str, body: VerifyRequest) -> dict[str, str]:
    verified_at = datetime.now(timezone.utc).isoformat()
    with _connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT payload_json FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Event not found")
        payload = json.loads(row["payload_json"])
        payload["review_status"] = "VERIFIED"
        payload["reviewer_note"] = body.reviewer_note
        payload["verified_at"] = verified_at
        connection.execute(
            """
            UPDATE events
            SET review_status = ?, verified_at = ?, payload_json = ?
            WHERE event_id = ?
            """,
            ("VERIFIED", verified_at, json.dumps(payload, ensure_ascii=False), event_id),
        )
        connection.commit()
    return {"event_id": event_id, "review_status": "VERIFIED", "verified_at": verified_at}


@app.post("/events/{event_id}/reject")
def reject_event(event_id: str, body: VerifyRequest) -> dict[str, str]:
    rejected_at = datetime.now(timezone.utc).isoformat()
    with _connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT payload_json FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Event not found")
        payload = json.loads(row["payload_json"])
        payload["review_status"] = "REJECTED"
        payload["reviewer_note"] = body.reviewer_note
        payload["rejected_at"] = rejected_at
        connection.execute(
            """
            UPDATE events
            SET review_status = ?, payload_json = ?
            WHERE event_id = ?
            """,
            ("REJECTED", json.dumps(payload, ensure_ascii=False), event_id),
        )
        connection.commit()
    return {"event_id": event_id, "review_status": "REJECTED", "rejected_at": rejected_at}


@app.post("/events/{event_id}/log-chain")
def log_to_chain(event_id: str, body: ChainLogRequest) -> dict[str, Any]:
    rpc = os.environ.get("SEPOLIA_RPC_URL")
    key = os.environ.get("DEPLOYER_PRIVATE_KEY")
    contract = os.environ.get("VIOLATION_LOGGER_ADDRESS")
    if not rpc or not key or not contract:
        raise HTTPException(
            status_code=503,
            detail="Chain logging is not configured. Set SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY, VIOLATION_LOGGER_ADDRESS.",
        )

    with _connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT review_status, candidate_type, payload_json FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Event not found")
        if row["review_status"] != "VERIFIED":
            raise HTTPException(status_code=400, detail="Only VERIFIED events may be logged on-chain")
        candidate_type = row["candidate_type"] or "unknown"

    from services.chain_client import ViolationChainClient

    client = ViolationChainClient(rpc, key, contract)
    timestamp = body.timestamp_utc or int(datetime.now(timezone.utc).timestamp())
    result = client.log_reviewed_violation(
        event_uuid=event_id,
        timestamp_utc=timestamp,
        candidate_type=candidate_type,
        evidence_hash_hex=body.evidence_hash_hex,
        plate_hash_hex=body.plate_hash_hex,
    )

    with _connect(DB_PATH) as connection:
        connection.execute(
            """
            UPDATE events
            SET chain_tx_hash = ?, chain_latency_seconds = ?
            WHERE event_id = ?
            """,
            (result.transaction_hash, result.latency_seconds, event_id),
        )
        connection.commit()

    return {
        "event_id": event_id,
        "transaction_hash": result.transaction_hash,
        "latency_seconds": round(result.latency_seconds, 3),
        "block_number": result.block_number,
    }


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    with _connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT event_id, video_filename, candidate_type, review_status, chain_tx_hash
            FROM events ORDER BY review_status, event_id LIMIT 200
            """
        ).fetchall()
    lines = "".join(
        f"<tr><td>{row['event_id']}</td><td>{row['video_filename']}</td>"
        f"<td>{row['candidate_type']}</td><td>{row['review_status']}</td>"
        f"<td>{row['chain_tx_hash'] or '-'}</td></tr>"
        for row in rows
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>STVD Review Dashboard</title></head>
<body>
<h1>Smart Traffic Violation — Review Dashboard (Prototype)</h1>
<p>Candidates are not confirmed violations until manually verified.</p>
<table border="1" cellpadding="6">
<tr><th>Event ID</th><th>Video</th><th>Type</th><th>Status</th><th>Chain Tx</th></tr>
{lines or '<tr><td colspan="5">No events imported yet.</td></tr>'}
</table>
</body></html>"""
