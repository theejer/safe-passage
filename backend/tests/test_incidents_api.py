"""Incident sync API tests."""

from app import create_app


def test_incidents_sync_route_persists_payload(monkeypatch):
    app = create_app("development")
    client = app.test_client()

    captured: dict = {"incident_count": 0, "sync_job": None}

    def _fake_upsert_incident(payload: dict) -> dict:
        captured["incident_count"] += 1
        return {"id": payload.get("id"), "user_id": payload.get("user_id")}

    def _fake_record_sync_job(user_id: str, idempotency_key: str, payload: dict, status: str = "accepted") -> dict:
        captured["sync_job"] = {
            "user_id": user_id,
            "idempotency_key": idempotency_key,
            "status": status,
            "payload": payload,
        }
        return captured["sync_job"]

    monkeypatch.setattr("app.routes.incidents.upsert_incident", _fake_upsert_incident)
    monkeypatch.setattr("app.routes.incidents.record_incident_sync_job", _fake_record_sync_job)

    response = client.post(
        "/incidents/sync",
        json={
            "idempotency_key": "sync-123",
            "incidents": [
                {
                    "incident_id": "11111111-1111-4111-8111-111111111111",
                    "user_id": "22222222-2222-4222-8222-222222222222",
                    "trip_id": "33333333-3333-4333-8333-333333333333",
                    "scenario_key": "medical",
                    "occurred_at": "2026-03-02T10:00:00Z",
                    "gps_lat": 25.0,
                    "gps_lng": 85.0,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["sync_status"] == "synced"
    assert body["synced_count"] == 1
    assert captured["incident_count"] == 1
    assert captured["sync_job"]["idempotency_key"] == "sync-123"
