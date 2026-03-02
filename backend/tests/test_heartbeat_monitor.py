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
        "list_segments_for_trip",
        lambda _trip_id: [
            {"segment_order": 1, "expected_offline_minutes": 90, "connectivity_risk": "severe"}
        ],
    )
    monkeypatch.setattr(heartbeat_monitor, "has_stage_1_confirmation", lambda *_args, **_kwargs: False)
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
