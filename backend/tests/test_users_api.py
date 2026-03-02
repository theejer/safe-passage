"""User API tests covering onboarding persistence behavior.

Verifies profile creation and emergency-contact updates through route boundaries.
"""

from app import create_app


def test_create_user_route_returns_created_user(monkeypatch):
    """POST /api/users should persist profile payload and return created user."""
    app = create_app("development")
    client = app.test_client()

    captured_payload: dict = {}

    def _fake_create_user(payload: dict) -> dict:
        captured_payload.update(payload)
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "full_name": payload["full_name"],
            "phone": payload["phone"],
            "emergency_contact": payload.get("emergency_contact"),
        }

    monkeypatch.setattr("app.routes.users.create_user", _fake_create_user)

    response = client.post(
        "/api/users",
        json={
            "full_name": "Aarti Kumari",
            "phone": "+919876543210",
            "emergency_contact": {
                "name": "Ravi",
                "phone": "+919100000001",
            },
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == "11111111-1111-1111-1111-111111111111"
    assert body["full_name"] == "Aarti Kumari"
    assert captured_payload["emergency_contact"]["name"] == "Ravi"


def test_patch_emergency_contact_route_returns_updated_user(monkeypatch):
    """PATCH /api/users/<id>/emergency-contact should return updated user data."""
    app = create_app("development")
    client = app.test_client()

    def _fake_update_contact(user_id: str, payload: dict) -> dict:
        return {
            "id": user_id,
            "full_name": "Aarti Kumari",
            "phone": "+919876543210",
            "emergency_contact": {
                "name": payload["name"],
                "phone": payload["phone"],
                "email": payload.get("email"),
            },
        }

    monkeypatch.setattr("app.routes.users.update_emergency_contact", _fake_update_contact)

    user_id = "11111111-1111-1111-1111-111111111111"
    response = client.patch(
        f"/api/users/{user_id}/emergency-contact",
        json={
            "name": "Ravi",
            "phone": "+919100000001",
            "email": "ravi@example.com",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["id"] == user_id
    assert body["emergency_contact"]["phone"] == "+919100000001"
