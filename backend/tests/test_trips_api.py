"""API tests for trip routes.

Regression coverage for local/demo IDs and route boundary behavior.
"""

from app import create_app
from app.models import trips as trips_model


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
