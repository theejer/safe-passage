"""Trip persistence helpers.

Trip routes and monitoring tasks use this module to read/write trip metadata.
"""

from app.extensions import get_supabase


def create_trip(payload: dict) -> dict:
    """Create a trip record that links a user to planned travel dates."""
    response = get_supabase().table("trips").insert(payload).execute()
    return response.data[0] if response.data else {}


def list_trips_by_user(user_id: str) -> list[dict]:
    """List all trips for a user to drive itinerary/risk views."""
    response = get_supabase().table("trips").select("*").eq("user_id", user_id).execute()
    return response.data or []


def get_trip_by_id(trip_id: str) -> dict:
    """Fetch a trip by id for ownership and monitoring checks."""
    response = get_supabase().table("trips").select("*").eq("id", trip_id).limit(1).execute()
    return response.data[0] if response.data else {}


def list_active_heartbeat_trips(today_iso_date: str) -> list[dict]:
    """List trips currently active and opted into heartbeat monitoring."""
    response = (
        get_supabase()
        .table("trips")
        .select("*")
        .eq("heartbeat_enabled", True)
        .lte("start_date", today_iso_date)
        .gte("end_date", today_iso_date)
        .execute()
    )
    return response.data or []
