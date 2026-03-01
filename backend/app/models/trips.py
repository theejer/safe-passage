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
