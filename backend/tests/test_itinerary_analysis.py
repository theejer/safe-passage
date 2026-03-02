"""Tests for itinerary analysis API/service flow.

Covers parser + risk engine integration through route boundary.
"""

from app import create_app
from app.routes import itinerary_analysis as itinerary_routes


def test_analyze_pipeline_returns_failed_for_empty_itinerary():
    app = create_app("development")
    client = app.test_client()

    response = client.post("/itinerary/analyze-pipeline", json={})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "failed"
    assert payload["stage"] == "input"


def test_analyze_pipeline_passes_through_success_payload(monkeypatch):
    app = create_app("development")
    client = app.test_client()

    def _fake_analyze_trip(payload):
        return {
            "status": "ok",
            "final_report": {"SCORE": {"value": 77, "justification": "ok"}},
            "judge": {"applied": False, "reason": "skipped_by_policy"},
            "score_breakdown": {"value": 77},
        }

    monkeypatch.setattr(itinerary_routes, "analyze_trip", _fake_analyze_trip)

    response = client.post(
        "/itinerary/analyze-pipeline",
        json={"itinerary": "Day 1: Patna museum visit", "trip_id": "not-a-real-db-id"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["final_report"]["SCORE"]["value"] == 77
    assert "saved" in payload
