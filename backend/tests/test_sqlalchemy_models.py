"""Regression tests for SQLAlchemy-backed model modules.

These tests use a fake SQLAlchemy engine to verify model functions execute
SQL paths and return normalized dict/list payloads.
"""

from __future__ import annotations

import json
from uuid import uuid4

from app.models import alerts as alerts_model
from app.models import heartbeats as heartbeats_model
from app.models import itinerary_risks as itinerary_risks_model
from app.models import risk_reports as risk_reports_model
from app.models import traveler_status as traveler_status_model


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeConnection:
    def __init__(self, strategy):
        self._strategy = strategy

    def execute(self, query, params=None):
        sql = str(query)
        bound_params = params or {}
        rows = self._strategy(sql, bound_params)
        if rows is None:
            rows = []
        return _FakeResult(rows)


class _FakeEngineContext:
    def __init__(self, strategy):
        self._strategy = strategy

    def __enter__(self):
        return _FakeConnection(self._strategy)

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, strategy):
        self._strategy = strategy

    def begin(self):
        return _FakeEngineContext(self._strategy)


def test_insert_heartbeat_uses_sqlalchemy_engine(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def strategy(sql: str, params: dict):
        calls.append((sql, params))
        assert "INSERT INTO heartbeats" in sql
        return [{"id": "hb_1", **params}]

    monkeypatch.setattr(heartbeats_model, "get_db_engine", lambda: _FakeEngine(strategy))

    payload = {
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "timestamp": "2026-03-02T10:00:00Z",
        "gps_lat": 24.75,
        "gps_lng": 84.37,
        "accuracy_meters": 20,
        "battery_percent": 78,
        "network_status": "online",
        "offline_minutes": 0,
        "source": "foreground",
        "emergency_phone": "+919111111111",
    }

    created = heartbeats_model.insert_heartbeat(payload)

    assert created["id"] == "hb_1"
    assert created["user_id"] == "usr_1"
    assert len(calls) == 1


def test_list_expected_offline_windows_for_trip_uses_sqlalchemy_engine(monkeypatch):
    expected_rows = [
        {"expected_offline_minutes": 30, "connectivity_risk": "moderate"},
        {"expected_offline_minutes": 60, "connectivity_risk": "severe"},
    ]

    def strategy(sql: str, params: dict):
        assert "FROM itinerary_risks" in sql
        assert params["trip_id"] == "trp_1"
        return expected_rows

    monkeypatch.setattr(itinerary_risks_model, "get_db_engine", lambda: _FakeEngine(strategy))

    rows = itinerary_risks_model.list_expected_offline_windows_for_trip("trp_1")

    assert rows == expected_rows


def test_save_risk_report_serializes_json(monkeypatch):
    trip_id = str(uuid4())

    def strategy(sql: str, params: dict):
        assert "INSERT INTO risk_reports" in sql
        assert params["trip_id"] == trip_id
        decoded = json.loads(params["report"])
        assert decoded["summary"] == "ok"
        return [{"id": "rr_1", "trip_id": trip_id, "report": decoded}]

    monkeypatch.setattr(risk_reports_model, "get_db_engine", lambda: _FakeEngine(strategy))

    created = risk_reports_model.save_risk_report(trip_id, {"summary": "ok", "days": []})

    assert created["id"] == "rr_1"
    assert created["report"]["summary"] == "ok"


def test_alert_event_create_and_recent_check(monkeypatch):
    user_id = str(uuid4())
    trip_id = str(uuid4())

    def strategy(sql: str, params: dict):
        if "INSERT INTO alert_events" in sql:
            assert params["user_id"] == user_id
            assert json.loads(params["channels"]) == ["telegram"]
            return [{"id": params["id"], "user_id": user_id, "trip_id": trip_id}]
        if "FROM alert_events" in sql:
            assert params["stage"] == "stage_1_initial_alert"
            return [{"id": "existing_alert"}]
        return []

    monkeypatch.setattr(alerts_model, "get_db_engine", lambda: _FakeEngine(strategy))

    created = alerts_model.create_alert_event(
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "trip_id": trip_id,
            "stage": "stage_1_initial_alert",
            "message": "msg",
            "channels": ["telegram"],
            "recipients": [{"phone": "+919999999999"}],
            "escalation_context": {"x": 1},
        }
    )
    recent = alerts_model.has_recent_stage_alert(user_id, trip_id, "stage_1_initial_alert", 30)

    assert created["user_id"] == user_id
    assert recent is True


def test_upsert_and_list_open_traveler_statuses(monkeypatch):
    user_id = str(uuid4())
    trip_id = str(uuid4())

    def strategy(sql: str, params: dict):
        if "INSERT INTO traveler_status" in sql:
            return [
                {
                    "id": params["id"],
                    "user_id": params["user_id"],
                    "trip_id": params["trip_id"],
                    "current_stage": params["current_stage"],
                    "monitoring_state": params["monitoring_state"],
                }
            ]
        if "FROM traveler_status" in sql and "monitoring_state <> 'resolved'" in sql:
            return [{"id": "sts_1", "user_id": user_id, "trip_id": trip_id, "monitoring_state": "active"}]
        return []

    monkeypatch.setattr(traveler_status_model, "get_db_engine", lambda: _FakeEngine(strategy))

    created = traveler_status_model.upsert_status(
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "trip_id": trip_id,
            "last_seen_at": "2026-03-02T10:05:00Z",
            "current_stage": "none",
            "monitoring_state": "active",
        }
    )
    open_rows = traveler_status_model.list_open_statuses()

    assert created["user_id"] == user_id
    assert open_rows[0]["monitoring_state"] == "active"


def test_update_status_rejects_non_uuid_keys():
    updated = traveler_status_model.update_status("demo-user", "trip-1", {"current_stage": "stage_1_initial_alert"})
    assert updated == {}
