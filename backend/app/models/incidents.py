"""Incident persistence helpers for MITIGATION sync flows."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import get_db_engine


def _is_uuid(value: str | None) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _is_missing_table_error(exc: Exception, table_name: str) -> bool:
    message = str(exc).lower()
    return f"no such table: {table_name}" in message or f'relation "{table_name}" does not exist' in message


def _ensure_incident_tables_for_sqlite() -> None:
    engine = get_db_engine()
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    trip_id TEXT,
                    scenario_key TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    gps_lat REAL,
                    gps_lng REAL,
                    notes TEXT,
                    severity TEXT,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS incident_sync_jobs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def upsert_incident(payload: dict) -> dict:
    query = text(
        """
        INSERT INTO incidents (
            id,
            user_id,
            trip_id,
            scenario_key,
            occurred_at,
            gps_lat,
            gps_lng,
            notes,
            severity,
            sync_status
        )
        VALUES (
            :id,
            :user_id,
            :trip_id,
            :scenario_key,
            :occurred_at,
            :gps_lat,
            :gps_lng,
            :notes,
            :severity,
            :sync_status
        )
        ON CONFLICT (id)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            trip_id = EXCLUDED.trip_id,
            scenario_key = EXCLUDED.scenario_key,
            occurred_at = EXCLUDED.occurred_at,
            gps_lat = EXCLUDED.gps_lat,
            gps_lng = EXCLUDED.gps_lng,
            notes = EXCLUDED.notes,
            severity = EXCLUDED.severity,
            sync_status = EXCLUDED.sync_status,
            updated_at = CURRENT_TIMESTAMP
        RETURNING *
        """
    )

    params = {
        "id": payload.get("id") or str(uuid4()),
        "user_id": payload.get("user_id"),
        "trip_id": payload.get("trip_id"),
        "scenario_key": payload.get("scenario_key"),
        "occurred_at": payload.get("occurred_at"),
        "gps_lat": payload.get("gps_lat"),
        "gps_lng": payload.get("gps_lng"),
        "notes": payload.get("notes"),
        "severity": payload.get("severity"),
        "sync_status": payload.get("sync_status") or "synced",
    }

    if not _is_uuid(params["id"]) or not _is_uuid(params["user_id"]):
        return {}

    engine = get_db_engine()

    def _upsert_once() -> dict:
        with engine.begin() as connection:
            row = connection.execute(query, params).mappings().first()
        return dict(row) if row else {}

    try:
        return _upsert_once()
    except (ProgrammingError, OperationalError) as exc:
        if not _is_missing_table_error(exc, "incidents"):
            raise
        _ensure_incident_tables_for_sqlite()
        return _upsert_once()


def record_incident_sync_job(user_id: str, idempotency_key: str, payload: dict, status: str = "accepted") -> dict:
    if not _is_uuid(user_id) or not idempotency_key:
        return {}

    query = text(
        """
        INSERT INTO incident_sync_jobs (
            id,
            user_id,
            idempotency_key,
            payload,
            status,
            retry_count,
            next_retry_at
        )
        VALUES (
            :id,
            :user_id,
            :idempotency_key,
            :payload,
            :status,
            0,
            NULL
        )
        ON CONFLICT (idempotency_key)
        DO UPDATE SET
            payload = EXCLUDED.payload,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP
        RETURNING *
        """
    )

    params = {
        "id": str(uuid4()),
        "user_id": user_id,
        "idempotency_key": idempotency_key,
        "payload": json.dumps(payload),
        "status": status,
    }

    engine = get_db_engine()

    def _insert_once() -> dict:
        with engine.begin() as connection:
            row = connection.execute(query, params).mappings().first()
        return dict(row) if row else {}

    try:
        return _insert_once()
    except (ProgrammingError, OperationalError) as exc:
        if not _is_missing_table_error(exc, "incident_sync_jobs"):
            raise
        _ensure_incident_tables_for_sqlite()
        return _insert_once()
