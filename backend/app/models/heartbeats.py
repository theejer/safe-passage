"""Heartbeat persistence helpers.

CURE monitoring uses this table to detect delayed reconnect and trigger escalation.
"""

from app.extensions import get_supabase


def insert_heartbeat(payload: dict) -> dict:
    """Store device heartbeat payload sent by mobile clients."""
    response = get_supabase().table("heartbeats").insert(payload).execute()
    return response.data[0] if response.data else {}


def list_recent_heartbeats(user_id: str, limit: int = 50) -> list[dict]:
    """Retrieve latest heartbeats for anomaly detection tasks."""
    response = (
        get_supabase()
        .table("heartbeats")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []
