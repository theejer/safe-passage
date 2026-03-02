"""Itinerary storage access.

Itinerary analysis routes and parser services persist normalized itinerary JSON here.
"""

import json
from uuid import UUID

from sqlalchemy import text

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def upsert_itinerary(trip_id: str, itinerary_json: dict) -> dict:
    """Store latest itinerary snapshot for a trip."""
    if not _is_uuid(trip_id):
        return {}

    query = text(
        """
        INSERT INTO itineraries (trip_id, itinerary_json)
        VALUES (:trip_id, CAST(:itinerary_json AS jsonb))
        ON CONFLICT (trip_id)
        DO UPDATE SET itinerary_json = EXCLUDED.itinerary_json
        RETURNING *
        """
    )
    with get_db_engine().begin() as connection:
        result = connection.execute(
            query,
            {"trip_id": trip_id, "itinerary_json": json.dumps(itinerary_json)},
        )
        row = result.mappings().first()
    return dict(row) if row else {}


def get_itinerary(trip_id: str) -> dict:
    """Fetch itinerary consumed by risk engine and heartbeat monitor."""
    if not _is_uuid(trip_id):
        return {}

    query = text("SELECT * FROM itineraries WHERE trip_id = :trip_id LIMIT 1")
    with get_db_engine().begin() as connection:
        result = connection.execute(query, {"trip_id": trip_id})
        row = result.mappings().first()
    return dict(row) if row else {}
