"""Itinerary storage access.

Itinerary analysis routes and parser services persist normalized itinerary JSON here.
"""

from app.extensions import get_supabase


def upsert_itinerary(trip_id: str, itinerary_json: dict) -> dict:
    """Store latest itinerary snapshot for a trip."""
    response = (
        get_supabase()
        .table("itineraries")
        .upsert({"trip_id": trip_id, "itinerary_json": itinerary_json}, on_conflict="trip_id")
        .execute()
    )
    return response.data[0] if response.data else {}


def get_itinerary(trip_id: str) -> dict:
    """Fetch itinerary consumed by risk engine and heartbeat monitor."""
    response = get_supabase().table("itineraries").select("*").eq("trip_id", trip_id).limit(1).execute()
    return response.data[0] if response.data else {}
