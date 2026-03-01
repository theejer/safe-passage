"""Traveler monitoring state persistence helpers."""

from __future__ import annotations

from app.extensions import get_supabase


def get_status_for_trip(user_id: str, trip_id: str) -> dict:
    """Return latest traveler status row for user/trip."""
    response = (
        get_supabase()
        .table("traveler_status")
        .select("*")
        .eq("user_id", user_id)
        .eq("trip_id", trip_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else {}


def upsert_status(payload: dict) -> dict:
    """Insert or update traveler status row keyed by user_id + trip_id."""
    response = (
        get_supabase()
        .table("traveler_status")
        .upsert(payload, on_conflict="user_id,trip_id")
        .execute()
    )
    return response.data[0] if response.data else {}


def update_status(user_id: str, trip_id: str, updates: dict) -> dict:
    """Apply partial update to traveler status."""
    response = (
        get_supabase()
        .table("traveler_status")
        .update(updates)
        .eq("user_id", user_id)
        .eq("trip_id", trip_id)
        .execute()
    )
    return response.data[0] if response.data else {}


def list_open_statuses() -> list[dict]:
    """List statuses still being monitored for staged alerts."""
    response = (
        get_supabase()
        .table("traveler_status")
        .select("*")
        .neq("monitoring_state", "resolved")
        .execute()
    )
    return response.data or []
