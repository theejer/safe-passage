"""Validation tests for incidents sync route."""

from app import create_app


def test_incidents_sync_requires_incidents_list():
    app = create_app("development")
    client = app.test_client()

    response = client.post("/incidents/sync", json={"idempotency_key": "sync-1"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "incidents list is required"


def test_incidents_sync_requires_user_id_on_first_incident():
    app = create_app("development")
    client = app.test_client()

    response = client.post(
        "/incidents/sync",
        json={
            "idempotency_key": "sync-1",
            "incidents": [
                {
                    "incident_id": "11111111-1111-4111-8111-111111111111",
                    "scenario_key": "medical",
                    "occurred_at": "2026-03-02T10:00:00Z",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "user_id is required"
