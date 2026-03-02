"""Heartbeat ingest and watchdog tests.

Covers:
- heartbeat insert path with FK-like prerequisites
- authenticated /heartbeat route normalization + 204 response
- watchdog timer evaluation and emergency alert triggering
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Flask

from app import create_app
from app.models.heartbeats import insert_heartbeat
from app.services import heartbeat_monitor


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
    def __init__(self, db: dict[str, list[dict]]):
        self._db = db
    def execute(self, query, params: dict):
        sql = str(query)
        if "INSERT INTO heartbeats" in sql:
            payload = dict(params)
            user_exists = any(item.get("id") == payload.get("user_id") for item in self._db["users"])
            trip_exists = any(item.get("id") == payload.get("trip_id") for item in self._db["trips"])
            if not user_exists:
                raise ValueError("foreign key violation: users")
            if not trip_exists:
                raise ValueError("foreign key violation: trips")
            self._db["heartbeats"].append(payload)
            return _FakeResult([payload])
        return _FakeResult([])


class _FakeEngineContext:
    def __init__(self, db: dict[str, list[dict]]):
        self._db = db

    def __enter__(self):
        return _FakeConnection(self._db)

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, db: dict[str, list[dict]]):
        self._db = db

    def begin(self):
        return _FakeEngineContext(self._db)


def test_insert_heartbeat_with_fk_seed_data(monkeypatch):
    """Heartbeats can be inserted when required FK records are seeded first."""
    fake_db = {
        "users": [{"id": "usr_1", "full_name": "Aarti", "phone": "+919100000001"}],
        "trips": [{"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True}],
        "heartbeats": [],
    }

    monkeypatch.setattr("app.models.heartbeats.get_db_engine", lambda: _FakeEngine(fake_db))

    created = insert_heartbeat(
        {
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T10:00:00Z",
            "gps_lat": 24.75,
            "gps_lng": 84.37,
            "network_status": "online",
        }
    )

    assert created["user_id"] == "usr_1"
    assert created["trip_id"] == "trp_1"
    assert len(fake_db["heartbeats"]) == 1


def test_heartbeat_route_ingest_normalizes_payload_and_returns_204(monkeypatch):
    """Route stores normalized heartbeat row after auth + trip ownership checks."""
    app = create_app("development")
    client = app.test_client()

    captured_rows: list[dict] = []
    processed_rows: list[dict] = []

    monkeypatch.setattr("app.routes.heartbeats.extract_bearer_token", lambda _req: "token")
    monkeypatch.setattr("app.routes.heartbeats.verify_supabase_user_id", lambda _token: "usr_1")
    monkeypatch.setattr(
        "app.routes.heartbeats.get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr("app.routes.heartbeats.insert_heartbeat", lambda row: captured_rows.append(row) or row)
    monkeypatch.setattr(
        "app.routes.heartbeats.process_heartbeat_ingest",
        lambda row: processed_rows.append(row) or {"ok": True},
    )

    response = client.post(
        "/heartbeat",
        json={
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T10:05:00Z",
            "gps": {"lat": 24.7541, "lng": 84.3795, "accuracy_meters": 20},
            "battery_percent": 42,
            "network_status": "offline",
            "offline_minutes": 35,
            "source": "background_fetch",
            "emergency_phone": "+919100000001",
        },
        headers={"Authorization": "Bearer fake"},
    )

    assert response.status_code == 204
    assert len(captured_rows) == 1
    assert len(processed_rows) == 1
    assert captured_rows[0]["gps_lat"] == 24.7541
    assert captured_rows[0]["gps_lng"] == 84.3795
    assert captured_rows[0]["accuracy_meters"] == 20


def test_heartbeat_route_rejects_missing_token_when_demo_fallback_disabled(monkeypatch):
    """Route rejects missing bearer token when demo fallback is disabled."""
    app = create_app("development")
    app.config["HEARTBEAT_DEMO_AUTH_FALLBACK"] = False
    client = app.test_client()

    monkeypatch.setattr("app.routes.heartbeats.extract_bearer_token", lambda _req: (_ for _ in ()).throw(ValueError("missing bearer token")))

    response = client.post(
        "/heartbeat",
        json={
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T10:05:00Z",
            "network_status": "offline",
            "source": "background_fetch",
        },
    )

    assert response.status_code == 401


def test_heartbeat_route_allows_demo_fallback_without_token(monkeypatch):
    """Route accepts heartbeat in development when demo auth fallback is enabled."""
    app = create_app("development")
    app.config["HEARTBEAT_DEMO_AUTH_FALLBACK"] = True
    client = app.test_client()

    captured_rows: list[dict] = []
    processed_rows: list[dict] = []

    monkeypatch.setattr("app.routes.heartbeats.extract_bearer_token", lambda _req: (_ for _ in ()).throw(ValueError("missing bearer token")))
    monkeypatch.setattr(
        "app.routes.heartbeats.get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr("app.routes.heartbeats.insert_heartbeat", lambda row: captured_rows.append(row) or row)
    monkeypatch.setattr(
        "app.routes.heartbeats.process_heartbeat_ingest",
        lambda row: processed_rows.append(row) or {"ok": True},
    )

    response = client.post(
        "/heartbeat",
        json={
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T10:05:00Z",
            "network_status": "offline",
            "source": "background_fetch",
        },
    )

    assert response.status_code == 204
    assert len(captured_rows) == 1
    assert len(processed_rows) == 1


def test_watchdog_timer_and_emergency_alert_for_enabled_trip(monkeypatch):
    """Watchdog computes offline timer for heartbeat-enabled trip and triggers stage alert."""
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=180)

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "list_active_heartbeat_trips",
        lambda _today: [
            {
                "id": "44444444-4444-4444-4444-444444444444",
                "user_id": "11111111-1111-1111-1111-111111111111",
                "heartbeat_enabled": True,
                "start_date": "2026-03-01",
                "end_date": "2026-03-05",
                "destination_country": "India",
            }
        ],
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_open_statuses",
        lambda: [
            {
                "id": "sts_1",
                "user_id": "11111111-1111-1111-1111-111111111111",
                "trip_id": "44444444-4444-4444-4444-444444444444",
                "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
                "last_seen_lat": 24.7541,
                "last_seen_lng": 84.3795,
                "last_battery_percent": 15,
                "connectivity_risk": "severe",
                "location_risk": "high",
                "current_stage": "none",
                "monitoring_state": "active",
                "emergency_phone": "+919100000001",
            }
        ],
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "user_id": "11111111-1111-1111-1111-111111111111",
            "heartbeat_enabled": True,
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_expected_offline_windows_for_trip",
        lambda _trip_id: [
            {"segment_order": 1, "expected_offline_minutes": 90, "connectivity_risk": "severe"}
        ],
    )
    monkeypatch.setattr(heartbeat_monitor, "has_stage_1_confirmation", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(heartbeat_monitor, "is_stage_1_rearmed", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": "Aarti Kumari",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.run_watchdog_cycle(now_utc=now)

    assert result["active_trip_count"] == 1
    assert result["result_count"] == 1

    row = result["results"][0]
    assert row["status"] == "alerted"
    assert row["offline_duration_minutes"] == 180
    assert row["trigger_stage"] == heartbeat_monitor.STAGE_1

    assert len(created_alerts) == 1
    assert len(sent_telegram) >= 1
    assert "can you contact" in sent_telegram[0][1].lower()
    assert "reply yes" in sent_telegram[0][1].lower()
    assert "or no" in sent_telegram[0][1].lower()
    assert "44444444-4444-4444-4444-444444444444" not in sent_telegram[0][1]
    assert "2026-03-01 to 2026-03-05" in sent_telegram[0][1]
    assert "india" in sent_telegram[0][1].lower()
    assert any(update["updates"].get("current_stage") for update in status_updates)


def test_watchdog_bootstraps_missing_status_with_stage_1_alert(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    upserted_statuses: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "list_active_heartbeat_trips",
        lambda _today: [
            {
                "id": "trp_1",
                "user_id": "usr_1",
                "title": "Bihar Route",
                "country": "India",
                "heartbeat_enabled": True,
                "start_date": "2026-03-01",
                "end_date": "2026-03-05",
            }
        ],
    )
    monkeypatch.setattr(heartbeat_monitor, "list_open_statuses", lambda: [])
    monkeypatch.setattr(heartbeat_monitor, "is_stage_1_rearmed", lambda *_args, **_kwargs: (True, "ok"))
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "full_name": "Aarti",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "trp_1",
            "traveler_name": "Aarti",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "upsert_status",
        lambda payload: upserted_statuses.append(payload) or payload,
    )

    result = heartbeat_monitor.run_watchdog_cycle(now_utc=now)

    assert result["active_trip_count"] == 1
    assert result["alerts_created_count"] == 1
    row = result["results"][0]
    assert row["status"] == "alerted"
    assert row["trigger_stage"] == heartbeat_monitor.STAGE_1
    assert row["reason"] == "missing-status-row"
    assert len(sent_telegram) == 1
    assert "reply yes" in sent_telegram[0][1].lower()
    assert "or no" in sent_telegram[0][1].lower()
    assert "trp_1" not in sent_telegram[0][1]
    assert "2026-03-01 to 2026-03-05" in sent_telegram[0][1]
    assert len(upserted_statuses) == 1
    assert upserted_statuses[0]["current_stage"] == heartbeat_monitor.STAGE_1


def test_stage1_suppressed_when_not_rearmed(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=140)

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "derive_monitoring_expectation",
        lambda _status, _trip_id, _now: {
            "expected_offline_minutes": 90,
            "threshold_multiplier": 1.5,
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "is_stage_1_rearmed", lambda *_args, **_kwargs: (False, "blocked-by-stage_2_escalation"))

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "current_stage": "none",
        "monitoring_state": "active",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "stage-1-suppressed"
    assert result["reason"] == "blocked-by-stage_2_escalation"
    assert result["offline_duration_minutes"] == 140


def test_bootstrap_stage1_suppressed_when_not_rearmed(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)

    sent_telegram: list[tuple[str, str]] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "list_active_heartbeat_trips",
        lambda _today: [
            {
                "id": "trp_1",
                "user_id": "usr_1",
                "title": "Bihar Route",
                "country": "India",
                "heartbeat_enabled": True,
                "start_date": "2026-03-01",
                "end_date": "2026-03-05",
            }
        ],
    )
    monkeypatch.setattr(heartbeat_monitor, "list_open_statuses", lambda: [])
    monkeypatch.setattr(heartbeat_monitor, "is_stage_1_rearmed", lambda *_args, **_kwargs: (False, "blocked-by-stage_1_initial_alert"))
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )

    result = heartbeat_monitor.run_watchdog_cycle(now_utc=now)

    assert result["active_trip_count"] == 1
    assert result["alerts_created_count"] == 0
    row = result["results"][0]
    assert row["status"] == "stage-1-suppressed"
    assert row["reason"] == "blocked-by-stage_1_initial_alert"
    assert len(sent_telegram) == 0


def test_stage1_message_expands_iso2_destination_country(monkeypatch):
    app = Flask("test")
    app.config["HEARTBEAT_FORCE_STAGE_1_TEST_MODE"] = True

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "user_id": "11111111-1111-1111-1111-111111111111",
            "heartbeat_enabled": True,
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "IN",
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": "Aarti Kumari",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "IN",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "trip_id": "44444444-4444-4444-4444-444444444444",
        "last_seen_at": "2026-03-02T00:00:00Z",
        "current_stage": "none",
        "monitoring_state": "active",
    }

    with app.app_context():
        result = heartbeat_monitor.evaluate_status_for_alert(
            status,
            datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc),
        )

    assert result["status"] == "alerted"
    assert len(sent_telegram) == 1
    assert "| India" in sent_telegram[0][1]


def test_reconnection_triggers_stage3_auto_recovery_alert(monkeypatch):
    """When user reconnects after prior escalation, stage-3 recovery alert is emitted."""
    created_alerts: list[dict] = []
    sent_telegram: list[tuple[str, str]] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_status_for_trip",
        lambda _user_id, _trip_id: {
            "id": "sts_1",
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "current_stage": heartbeat_monitor.STAGE_2,
            "monitoring_state": "alerted",
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "upsert_status", lambda payload: payload)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.process_heartbeat_ingest(
        {
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T12:10:00Z",
            "gps_lat": 24.7541,
            "gps_lng": 84.3795,
            "network_status": "online",
            "battery_percent": 55,
            "emergency_phone": "+919100000001",
        }
    )

    assert result["current_stage"] == heartbeat_monitor.STAGE_2

    assert len(created_alerts) == 1
    assert created_alerts[0]["stage"] == heartbeat_monitor.STAGE_3
    assert len(sent_telegram) >= 1
    assert "back online" in created_alerts[0]["message"].lower()

    assert len(status_updates) == 1
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_3
    assert status_updates[0]["updates"]["monitoring_state"] == "resolved"


def test_reconnection_does_not_trigger_stage3_when_still_offline(monkeypatch):
    """Do not emit recovery when new heartbeat is not online."""
    created_alerts: list[dict] = []
    sent_telegram: list[tuple[str, str]] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_status_for_trip",
        lambda _user_id, _trip_id: {
            "id": "sts_1",
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "current_stage": heartbeat_monitor.STAGE_1,
            "monitoring_state": "alerted",
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "upsert_status", lambda payload: payload)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.process_heartbeat_ingest(
        {
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T12:15:00Z",
            "gps_lat": 24.7541,
            "gps_lng": 84.3795,
            "network_status": "offline",
            "battery_percent": 48,
            "emergency_phone": "+919100000001",
        }
    )

    assert result["current_stage"] == heartbeat_monitor.STAGE_1
    assert created_alerts == []
    assert sent_telegram == []
    assert status_updates == []


def test_reconnection_does_not_trigger_stage3_when_prior_stage_none(monkeypatch):
    """Do not emit recovery when there was no prior escalation stage."""
    created_alerts: list[dict] = []
    sent_telegram: list[tuple[str, str]] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_status_for_trip",
        lambda _user_id, _trip_id: {
            "id": "sts_1",
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "current_stage": "none",
            "monitoring_state": "active",
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "upsert_status", lambda payload: payload)
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.process_heartbeat_ingest(
        {
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "timestamp": "2026-03-02T12:20:00Z",
            "gps_lat": 24.7541,
            "gps_lng": 84.3795,
            "network_status": "online",
            "battery_percent": 70,
            "emergency_phone": "+919100000001",
        }
    )

    assert result["current_stage"] == "none"
    assert created_alerts == []
    assert sent_telegram == []
    assert status_updates == []


def test_force_stage_1_test_mode_alerts_even_without_last_seen(monkeypatch):
    app = Flask("test")
    app.config["HEARTBEAT_FORCE_STAGE_1_TEST_MODE"] = True

    created_alerts: list[dict] = []
    sent_telegram: list[tuple[str, str]] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": None,
        "current_stage": "none",
        "monitoring_state": "active",
    }

    with app.app_context():
        result = heartbeat_monitor.evaluate_status_for_alert(status, datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc))

    assert result["status"] == "alerted"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_1
    assert len(created_alerts) == 1
    assert created_alerts[0]["escalation_context"]["test_mode"] is True
    assert len(sent_telegram) == 1
    assert "[TEST MODE]" in created_alerts[0]["message"]
    assert len(status_updates) == 1


def test_watchdog_accepts_datetime_last_seen_without_crash(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=60)

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id: 90)

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen,
        "connectivity_risk": "moderate",
        "current_stage": "none",
        "monitoring_state": "active",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["trip_id"] == "trp_1"
    assert result["status"] == "within-window"
    assert result["offline_duration_minutes"] == 60


def test_force_mode_stage1_resends_for_existing_stage1_when_not_deduped(monkeypatch):
    app = Flask("test")
    app.config["HEARTBEAT_FORCE_STAGE_1_TEST_MODE"] = True

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "user_id": "11111111-1111-1111-1111-111111111111",
            "heartbeat_enabled": True,
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": "Aarti Kumari",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "44444444-4444-4444-4444-444444444444",
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "trip_id": "44444444-4444-4444-4444-444444444444",
        "last_seen_at": "2026-03-02T00:00:00Z",
        "current_stage": heartbeat_monitor.STAGE_1,
        "monitoring_state": "alerted",
    }

    with app.app_context():
        result = heartbeat_monitor.evaluate_status_for_alert(
            status,
            datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc),
        )

    assert result["status"] == "alerted"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_1
    assert len(created_alerts) == 1
    assert len(sent_telegram) == 1
    assert len(status_updates) == 1


def test_stage2_waits_for_contact_confirmation(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=244)

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_latest_trip_stage_alert",
        lambda *_args, **_kwargs: {"stage": heartbeat_monitor.STAGE_1},
    )
    monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id: 90)
    monkeypatch.setattr(heartbeat_monitor, "has_stage_1_confirmation", lambda *_args, **_kwargs: False)

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "last_battery_percent": 18,
        "connectivity_risk": "moderate",
        "current_stage": heartbeat_monitor.STAGE_1,
        "monitoring_state": "alerted",
        "last_stage_change_at": (now - timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "awaiting-contact-confirmation"
    assert result["requires_confirmation"] is True
    assert result["current_stage"] == heartbeat_monitor.STAGE_1


def test_stage2_triggers_after_contact_confirmation(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=244)

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_latest_trip_stage_alert",
        lambda *_args, **_kwargs: {"stage": heartbeat_monitor.STAGE_1},
    )
    monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id: 90)
    monkeypatch.setattr(heartbeat_monitor, "has_stage_1_confirmation", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "last_seen_lat": 24.7541,
        "last_seen_lng": 84.3795,
        "last_battery_percent": 18,
        "connectivity_risk": "moderate",
        "location_risk": "high",
        "current_stage": heartbeat_monitor.STAGE_1,
        "monitoring_state": "alerted",
        "last_stage_change_at": (now - timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "alerted"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_2
    assert len(created_alerts) == 1
    assert created_alerts[0]["stage"] == heartbeat_monitor.STAGE_2
    assert len(sent_telegram) == 1
    assert any(item["updates"].get("current_stage") == heartbeat_monitor.STAGE_2 for item in status_updates)


def test_derive_monitoring_expectation_blends_connectivity_history_and_persists(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id: 90)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_itinerary",
        lambda _trip_id: {
            "itinerary_json": {
                "trip": {
                    "days": [
                        {
                            "date": "2026-03-02",
                            "locations": [
                                {
                                    "type": "visit",
                                    "name": "Patna",
                                    "geo": {"lat": 25.5941, "lng": 85.1376},
                                    "time": {"start_local": "2026-03-02T11:30:00+05:30"},
                                    "risk_queries": {"is_overnight": False},
                                }
                            ],
                        }
                    ]
                }
            }
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "predict_connectivity_for_latlon",
        lambda _lat, _lng: {
            "expected_offline_minutes": 80,
            "confidence": 0.72,
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_recent_heartbeats",
        lambda _user_id, limit=120: [
            {"timestamp": "2026-03-02T08:00:00Z", "offline_minutes": 20},
            {"timestamp": "2026-03-02T07:10:00Z", "offline_minutes": 35},
            {"timestamp": "2026-03-02T06:20:00Z", "offline_minutes": 30},
            {"timestamp": "2026-03-02T05:20:00Z", "offline_minutes": 40},
        ],
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_latest_monitoring_expectation",
        lambda _trip_id: {
            "expected_offline_minutes": 100,
            "threshold_multiplier": 1.55,
        },
    )

    persisted_payload: dict = {}

    def _fake_upsert_monitoring_expectation(**kwargs):
        persisted_payload.update(kwargs)
        return kwargs

    monkeypatch.setattr(heartbeat_monitor, "upsert_monitoring_expectation", _fake_upsert_monitoring_expectation)

    result = heartbeat_monitor.derive_monitoring_expectation(
        status={"user_id": "usr_1"},
        trip_id="trp_1",
        now_utc=now,
    )

    assert 15 <= result["expected_offline_minutes"] <= 240
    assert 1.2 <= result["threshold_multiplier"] <= 2.0
    assert persisted_payload["trip_id"] == "trp_1"
    assert "location_name" in persisted_payload


def test_stage1_does_not_trigger_below_1_5x_expected(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=100)

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "derive_monitoring_expectation",
        lambda _status, _trip_id, _now: {
            "expected_offline_minutes": 90,
            "threshold_multiplier": 1.5,
        },
    )

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "current_stage": "none",
        "monitoring_state": "active",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "within-window"
    assert result["offline_duration_minutes"] == 100
    assert result["expected_offline_minutes"] == 90


def test_stage1_triggers_when_over_1_5x_expected(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=140)

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "derive_monitoring_expectation",
        lambda _status, _trip_id, _now: {
            "expected_offline_minutes": 90,
            "threshold_multiplier": 1.5,
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "full_name": "Aarti",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(heartbeat_monitor, "update_status", lambda *_args, **_kwargs: {"ok": True})

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "current_stage": "none",
        "monitoring_state": "active",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "alerted"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_1
    assert result["offline_duration_minutes"] == 140
    assert result["expected_offline_minutes"] == 90
    assert len(created_alerts) == 1
    assert len(sent_telegram) == 1


def test_derive_expected_offline_minutes_falls_back_when_segments_query_fails(monkeypatch):
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_expected_offline_windows_for_trip",
        lambda _trip_id: (_ for _ in ()).throw(RuntimeError("relation itinerary_risks does not exist")),
    )

    result = heartbeat_monitor.derive_expected_offline_minutes("trp_1")

    assert result == 90


def test_monitoring_expectation_calculation_demo_prints(monkeypatch):
    """Demonstrate expectation outputs for multiple factor profiles.

    Run with `-s` to see printed values in terminal.
    """
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    scenarios = [
        {
            "name": "high-risk-poor-connectivity",
            "baseline": 90,
            "prediction": {"expected_offline_minutes": 130, "confidence": 0.22},
            "heartbeats": [
                {"timestamp": "2026-03-02T11:30:00Z", "offline_minutes": 80},
                {"timestamp": "2026-03-02T10:10:00Z", "offline_minutes": 95},
                {"timestamp": "2026-03-02T08:50:00Z", "offline_minutes": 70},
                {"timestamp": "2026-03-02T07:35:00Z", "offline_minutes": 105},
            ],
            "previous": {"expected_offline_minutes": 120, "threshold_multiplier": 1.72},
            "location_type": "transit",
            "is_overnight": True,
        },
        {
            "name": "low-risk-good-connectivity",
            "baseline": 90,
            "prediction": {"expected_offline_minutes": 28, "confidence": 0.9},
            "heartbeats": [
                {"timestamp": "2026-03-02T11:50:00Z", "offline_minutes": 10},
                {"timestamp": "2026-03-02T11:35:00Z", "offline_minutes": 8},
                {"timestamp": "2026-03-02T11:20:00Z", "offline_minutes": 12},
                {"timestamp": "2026-03-02T11:05:00Z", "offline_minutes": 9},
            ],
            "previous": {"expected_offline_minutes": 40, "threshold_multiplier": 1.35},
            "location_type": "visit",
            "is_overnight": False,
        },
        {
            "name": "sparse-history-moderate-connectivity",
            "baseline": 90,
            "prediction": {"expected_offline_minutes": 55, "confidence": 0.45},
            "heartbeats": [],
            "previous": {},
            "location_type": "visit",
            "is_overnight": False,
        },
    ]

    printed_rows: list[dict] = []

    for scenario in scenarios:
        monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id, s=scenario: s["baseline"])
        monkeypatch.setattr(
            heartbeat_monitor,
            "get_itinerary",
            lambda _trip_id, s=scenario: {
                "itinerary_json": {
                    "trip": {
                        "days": [
                            {
                                "date": "2026-03-02",
                                "locations": [
                                    {
                                        "type": s["location_type"],
                                        "name": "Demo Point",
                                        "geo": {"lat": 25.6, "lng": 85.1},
                                        "time": {"start_local": "2026-03-02T11:30:00+05:30"},
                                        "risk_queries": {"is_overnight": s["is_overnight"]},
                                    }
                                ],
                            }
                        ]
                    }
                }
            },
        )
        monkeypatch.setattr(
            heartbeat_monitor,
            "predict_connectivity_for_latlon",
            lambda _lat, _lng, s=scenario: s["prediction"],
        )
        monkeypatch.setattr(
            heartbeat_monitor,
            "list_recent_heartbeats",
            lambda _user_id, limit=120, s=scenario: s["heartbeats"],
        )
        monkeypatch.setattr(
            heartbeat_monitor,
            "get_latest_monitoring_expectation",
            lambda _trip_id, s=scenario: s["previous"],
        )
        monkeypatch.setattr(
            heartbeat_monitor,
            "upsert_monitoring_expectation",
            lambda **kwargs: kwargs,
        )

        result = heartbeat_monitor.derive_monitoring_expectation(
            status={"user_id": "usr_1"},
            trip_id="trp_1",
            now_utc=now,
        )

        row = {
            "scenario": scenario["name"],
            "expected_offline_minutes": result["expected_offline_minutes"],
            "threshold_multiplier": result["threshold_multiplier"],
            "confidence": result["confidence"],
            "history_reliability": result["history_reliability"],
            "volatility": result["volatility"],
            "location_name": result["location_name"],
        }
        printed_rows.append(row)
        print(f"[expectation-demo] {row}")

    assert len(printed_rows) == 3
    assert printed_rows[0]["expected_offline_minutes"] > printed_rows[1]["expected_offline_minutes"]


def test_apply_stage1_yes_sends_personalized_stage3_recovery(monkeypatch):
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_status_for_trip",
        lambda _user_id, _trip_id: {
            "id": "sts_1",
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "current_stage": heartbeat_monitor.STAGE_1,
            "monitoring_state": "alerted",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Anil Sharma",
                "phone": "+6592000002",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "trp_1",
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda _chat_id, _message, bot_token=None: {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.apply_stage_1_contact_response(
        user_id="usr_1",
        trip_id="trp_1",
        can_contact=True,
        confirmed_by="Anil Sharma",
        source="telegram",
    )

    assert result["status"] == "deescalated"
    assert result["stage"] == heartbeat_monitor.STAGE_3
    assert len(created_alerts) == 1
    assert "Thank you Anil Sharma" in created_alerts[0]["message"]
    assert "safety buffer" in created_alerts[0]["message"]
    assert created_alerts[0]["escalation_context"]["rearm_buffer_minutes"] == heartbeat_monitor.STAGE_1_REARM_BUFFER_MINUTES
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_3


def test_apply_stage1_no_escalates_with_bihar_emergency_details(monkeypatch):
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_status_for_trip",
        lambda _user_id, _trip_id: {
            "id": "sts_1",
            "user_id": "usr_1",
            "trip_id": "trp_1",
            "current_stage": heartbeat_monitor.STAGE_1,
            "monitoring_state": "alerted",
            "last_seen_at": "2026-03-02T07:00:00Z",
            "last_seen_lat": 25.5941,
            "last_seen_lng": 85.1376,
            "last_battery_percent": 17,
            "last_network_status": "offline",
            "location_risk": "high",
            "connectivity_risk": "severe",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Anil Sharma",
                "phone": "+6592000002",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_alert_context",
        lambda _trip_id: {
            "id": "trp_1",
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "record_stage_1_contact_confirmation",
        lambda **_kwargs: {"status": "confirmed"},
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(heartbeat_monitor, "derive_expected_offline_minutes", lambda _trip_id: 90)
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda _chat_id, _message, bot_token=None: {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    result = heartbeat_monitor.apply_stage_1_contact_response(
        user_id="usr_1",
        trip_id="trp_1",
        can_contact=False,
        confirmed_by="Anil Sharma",
        source="telegram",
    )

    assert result["status"] == "escalated"
    assert result["stage"] == heartbeat_monitor.STAGE_2
    assert len(created_alerts) == 1
    stage_2_message = created_alerts[0]["message"]
    assert "STAGE 2 ESCALATION" in stage_2_message
    assert "LAST KNOWN STATUS" in stage_2_message
    assert "Last Heartbeat:" in stage_2_message
    assert "Bihar, India" in stage_2_message
    assert "National Emergency: 112" in stage_2_message
    assert "SINGAPORE EMBASSY / CONSULAR SUPPORT" in stage_2_message
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_2


def test_watchdog_online_status_recovers_to_stage3(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {
            "id": "trp_1",
            "user_id": "usr_1",
            "heartbeat_enabled": True,
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "full_name": "Aarti Kumari",
            "emergency_contact": {
                "name": "Anil Sharma",
                "phone": "+6592000002",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": "2026-03-02T12:00:00Z",
        "last_seen_lat": 25.5941,
        "last_seen_lng": 85.1376,
        "last_network_status": "online",
        "current_stage": heartbeat_monitor.STAGE_2,
        "monitoring_state": "alerted",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "recovered"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_3
    assert len(created_alerts) == 1
    assert "Heartbeat detected at" in created_alerts[0]["message"]
    assert len(sent_telegram) == 1
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_3


def test_stage2_message_explicitly_states_no_heartbeat_when_missing_data():
    message = heartbeat_monitor._build_stage_2_message(
        alert_context={
            "traveler_name": "Aarti Kumari",
            "start_date": "2026-03-01",
            "end_date": "2026-03-05",
            "destination_country": "India",
        },
        status={
            "last_seen_at": None,
            "last_seen_lat": None,
            "last_seen_lng": None,
            "last_battery_percent": None,
            "last_network_status": None,
            "location_risk": None,
            "connectivity_risk": None,
        },
        offline_duration_minutes=0,
        adjusted_expected=90,
    )

    assert "No heartbeat received yet" in message
    assert "No GPS fix recorded yet" in message
    assert "No battery telemetry received yet" in message
    assert "No network telemetry received yet" in message


def test_stage1_resends_when_history_missing(monkeypatch):
    now = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)
    last_seen = now - timedelta(minutes=300)

    sent_telegram: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "get_trip_by_id",
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "derive_monitoring_expectation",
        lambda _status, _trip_id, _now: {
            "expected_offline_minutes": 90,
            "threshold_multiplier": 1.5,
        },
    )
    monkeypatch.setattr(heartbeat_monitor, "get_latest_trip_stage_alert", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {
                "name": "Anil Sharma",
                "phone": "+6592000002",
                "telegram_chat_id": "123456",
                "telegram_bot_active": True,
            },
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_telegram_alert",
        lambda chat_id, message, bot_token=None: sent_telegram.append((chat_id, message)) or {"queued": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "create_alert_event",
        lambda payload: created_alerts.append(payload) or payload,
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "update_status",
        lambda user_id, trip_id, updates: status_updates.append(
            {"user_id": user_id, "trip_id": trip_id, "updates": updates}
        )
        or {"ok": True},
    )

    status = {
        "id": "sts_1",
        "user_id": "usr_1",
        "trip_id": "trp_1",
        "last_seen_at": last_seen.isoformat().replace("+00:00", "Z"),
        "last_network_status": "offline",
        "current_stage": heartbeat_monitor.STAGE_1,
        "monitoring_state": "alerted",
    }

    result = heartbeat_monitor.evaluate_status_for_alert(status, now)

    assert result["status"] == "alerted"
    assert result["trigger_stage"] == heartbeat_monitor.STAGE_1
    assert len(created_alerts) == 1
    assert len(sent_telegram) == 1
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_1
