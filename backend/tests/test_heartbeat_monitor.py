"""Heartbeat ingest and watchdog tests.

Covers:
- heartbeat insert path with FK-like prerequisites
- authenticated /heartbeat route normalization + 204 response
- watchdog timer evaluation and emergency alert triggering
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app import create_app
from app.models.heartbeats import insert_heartbeat
from app.services import heartbeat_monitor


@dataclass
class _Result:
    data: list[dict]


class _FakeTable:
    def __init__(self, db: dict[str, list[dict]], name: str):
        self._db = db
        self._name = name
        self._rows = list(db.get(name, []))
        self._insert_payload: dict | None = None
        self._limit: int | None = None

    def insert(self, payload: dict):
        self._insert_payload = payload
        return self

    def select(self, _fields: str):
        return self

    def eq(self, field: str, value):
        self._rows = [row for row in self._rows if row.get(field) == value]
        return self

    def order(self, _field: str, desc: bool = False):
        self._rows = sorted(self._rows, key=lambda row: row.get(_field), reverse=desc)
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    def execute(self):
        if self._insert_payload is not None:
            payload = dict(self._insert_payload)
            if self._name == "heartbeats":
                user_exists = any(item.get("id") == payload.get("user_id") for item in self._db["users"])
                trip_exists = any(item.get("id") == payload.get("trip_id") for item in self._db["trips"])
                if not user_exists:
                    raise ValueError("foreign key violation: users")
                if not trip_exists:
                    raise ValueError("foreign key violation: trips")
            self._db[self._name].append(payload)
            return _Result([payload])

        rows = self._rows
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)


class _FakeSupabase:
    def __init__(self, db: dict[str, list[dict]]):
        self._db = db

    def table(self, name: str):
        return _FakeTable(self._db, name)


def test_insert_heartbeat_with_fk_seed_data(monkeypatch):
    """Heartbeats can be inserted when required FK records are seeded first."""
    fake_db = {
        "users": [{"id": "usr_1", "full_name": "Aarti", "phone": "+919100000001"}],
        "trips": [{"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True}],
        "heartbeats": [],
    }

    monkeypatch.setattr("app.models.heartbeats.get_supabase", lambda: _FakeSupabase(fake_db))

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

    sent_sms: list[tuple[str, str]] = []
    created_alerts: list[dict] = []
    status_updates: list[dict] = []

    monkeypatch.setattr(
        heartbeat_monitor,
        "list_active_heartbeat_trips",
        lambda _today: [
            {
                "id": "trp_1",
                "user_id": "usr_1",
                "heartbeat_enabled": True,
                "start_date": "2026-03-01",
                "end_date": "2026-03-05",
            }
        ],
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_open_statuses",
        lambda: [
            {
                "id": "sts_1",
                "user_id": "usr_1",
                "trip_id": "trp_1",
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
        lambda _trip_id: {"id": "trp_1", "user_id": "usr_1", "heartbeat_enabled": True},
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "list_segments_for_trip",
        lambda _trip_id: [
            {"segment_order": 1, "expected_offline_minutes": 90, "connectivity_risk": "severe"}
        ],
    )
    monkeypatch.setattr(heartbeat_monitor, "has_recent_stage_alert", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        heartbeat_monitor,
        "get_user_by_id",
        lambda _user_id: {
            "id": "usr_1",
            "emergency_contact": {"name": "Ravi", "phone": "+919100000001"},
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_sms_alert",
        lambda phone, message: sent_sms.append((phone, message)) or {"queued": True},
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
    assert row["trigger_stage"] in {
        heartbeat_monitor.STAGE_1,
        heartbeat_monitor.STAGE_2,
    }

    assert len(created_alerts) == 1
    assert len(sent_sms) >= 1
    assert any(update["updates"].get("current_stage") for update in status_updates)


def test_reconnection_triggers_stage3_auto_recovery_alert(monkeypatch):
    """When user reconnects after prior escalation, stage-3 recovery alert is emitted."""
    created_alerts: list[dict] = []
    sent_sms: list[tuple[str, str]] = []
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
            "emergency_contact": {"name": "Ravi", "phone": "+919100000001"},
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_sms_alert",
        lambda phone, message: sent_sms.append((phone, message)) or {"queued": True},
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
    assert len(sent_sms) >= 1
    assert "back online" in created_alerts[0]["message"].lower()

    assert len(status_updates) == 1
    assert status_updates[0]["updates"]["current_stage"] == heartbeat_monitor.STAGE_3
    assert status_updates[0]["updates"]["monitoring_state"] == "resolved"


def test_reconnection_does_not_trigger_stage3_when_still_offline(monkeypatch):
    """Do not emit recovery when new heartbeat is not online."""
    created_alerts: list[dict] = []
    sent_sms: list[tuple[str, str]] = []
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
            "emergency_contact": {"name": "Ravi", "phone": "+919100000001"},
        },
    )
    monkeypatch.setattr(
        heartbeat_monitor,
        "send_sms_alert",
        lambda phone, message: sent_sms.append((phone, message)) or {"queued": True},
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
    assert sent_sms == []
    assert status_updates == []


def test_reconnection_does_not_trigger_stage3_when_prior_stage_none(monkeypatch):
    """Do not emit recovery when there was no prior escalation stage."""
    created_alerts: list[dict] = []
    sent_sms: list[tuple[str, str]] = []
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
        "send_sms_alert",
        lambda phone, message: sent_sms.append((phone, message)) or {"queued": True},
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
    assert sent_sms == []
    assert status_updates == []
