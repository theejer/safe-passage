"""API tests for trip routes.

Regression coverage for local/demo IDs and route boundary behavior.
"""

import io

from app import create_app
from app.models import trips as trips_model
from app.routes import trips as trips_routes


def test_list_trips_non_uuid_short_circuits_database(monkeypatch):
    """Non-UUID demo ids should safely return empty list without DB access."""

    def _unexpected_db_access():
        raise AssertionError("DB should not be accessed for non-UUID user_id")

    monkeypatch.setattr(trips_model, "get_db_engine", _unexpected_db_access)

    result = trips_model.list_trips_by_user("demo-user")

    assert result == []


def test_trips_route_returns_200_for_demo_user_id():
    """Route should not 500 for local/demo identifiers used by frontend."""
    app = create_app("development")
    client = app.test_client()

    response = client.get("/trips?user_id=demo-user", headers={"Origin": "http://localhost:8081"})

    assert response.status_code == 200
    assert response.get_json() == {"items": []}
    assert response.headers.get("Access-Control-Allow-Origin") is not None


def test_upload_pdf_route_passes_trip_dates_context(monkeypatch):
    app = create_app("development")
    client = app.test_client()
    captured: dict = {}

    def _fake_get_trip_by_id(_trip_id: str):
        return {
            "title": "Japan Sprint",
            "start_date": "2026-04-01",
            "end_date": "2026-04-05",
        }

    def _fake_extract_itinerary_from_document(_file_path: str, *, parser_context=None):
        captured["parser_context"] = parser_context
        return {
            "days": [
                {
                    "date": "2026-04-01",
                    "locations": [{"name": "Tokyo"}],
                    "accommodation": "Hotel",
                }
            ],
            "meta": {},
        }

    monkeypatch.setattr(trips_routes, "get_trip_by_id", _fake_get_trip_by_id)
    monkeypatch.setattr(trips_routes, "extract_itinerary_from_document", _fake_extract_itinerary_from_document)
    monkeypatch.setattr(trips_routes, "upsert_itinerary", lambda *_args, **_kwargs: None)

    response = client.post(
        "/trips/upload-pdf",
        data={
            "trip_id": "0e5c9d1c-f34d-4a7e-962d-18e26d8f275d",
            "file": (io.BytesIO(b"fake itinerary"), "itinerary.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert captured["parser_context"]["trip_name"] == "Japan Sprint"
    assert captured["parser_context"]["start_date"] == "2026-04-01"
    assert captured["parser_context"]["end_date"] == "2026-04-05"
