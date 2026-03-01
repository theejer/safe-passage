"""Itinerary segment persistence helpers for watchdog expectations."""

from __future__ import annotations

from app.extensions import get_supabase


def list_segments_for_trip(trip_id: str) -> list[dict]:
    """List trip segments with expected offline windows."""
    response = (
        get_supabase()
        .table("itinerary_segments")
        .select("*")
        .eq("trip_id", trip_id)
        .order("segment_order")
        .execute()
    )
    return response.data or []
