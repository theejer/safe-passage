"""Tests for user model ID handling with client-provided UUIDs."""

from __future__ import annotations

from uuid import UUID

from app.models import users as users_model


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeConnection:
    def __init__(self, strategy):
        self._strategy = strategy

    def execute(self, query, params=None):
        sql = str(query)
        bound_params = params or {}
        rows = self._strategy(sql, bound_params)
        return _FakeResult(rows or [])


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


def test_create_user_uses_client_uuid_when_valid(monkeypatch):
    provided_id = "11111111-1111-4111-8111-111111111111"
    captured = {"inserted_id": None}

    def strategy(sql: str, params: dict):
        if "INSERT INTO users" in sql:
            captured["inserted_id"] = params["id"]
            return [{"id": params["id"], "full_name": params["full_name"], "phone": params["phone"]}]
        return []

    monkeypatch.setattr(users_model, "get_db_engine", lambda: _FakeEngine(strategy))
    monkeypatch.setattr(users_model, "_attach_primary_emergency_contact", lambda row: row)

    created = users_model.create_user({"id": provided_id, "full_name": "Aarti", "phone": "+919111111111"})

    assert created["id"] == provided_id
    assert captured["inserted_id"] == provided_id


def test_create_user_generates_uuid_when_client_id_invalid(monkeypatch):
    captured = {"inserted_id": None}

    def strategy(sql: str, params: dict):
        if "INSERT INTO users" in sql:
            captured["inserted_id"] = params["id"]
            return [{"id": params["id"], "full_name": params["full_name"], "phone": params["phone"]}]
        return []

    monkeypatch.setattr(users_model, "get_db_engine", lambda: _FakeEngine(strategy))
    monkeypatch.setattr(users_model, "_attach_primary_emergency_contact", lambda row: row)

    created = users_model.create_user({"id": "local_user_123", "full_name": "Aarti", "phone": "+919111111111"})

    assert created["id"] == captured["inserted_id"]
    UUID(str(created["id"]))
