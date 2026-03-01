"""Alert event persistence wrappers used by watchdog escalation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.extensions import get_supabase


def create_alert_event(payload: dict) -> dict:
    """Insert alert event row and return created record."""
    response = get_supabase().table("alert_events").insert(payload).execute()
    return response.data[0] if response.data else {}


def has_recent_stage_alert(user_id: str, trip_id: str, stage: str, within_minutes: int) -> bool:
    """Check if same stage alert already emitted recently to avoid spam."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=within_minutes)).isoformat()
    response = (
        get_supabase()
        .table("alert_events")
        .select("id")
        .eq("user_id", user_id)
        .eq("trip_id", trip_id)
        .eq("stage", stage)
        .gte("created_at", since)
        .limit(1)
        .execute()
    )
    return bool(response.data)
