"""Itinerary risk window persistence helpers for watchdog expectations."""

from __future__ import annotations

from sqlalchemy import text

from app.extensions import get_db_engine


def list_expected_offline_windows_for_trip(trip_id: str) -> list[dict]:
    """List positive expected-offline windows derived from itinerary risk analysis."""
    query = text(
        """
        SELECT expected_offline_minutes, connectivity_risk
        FROM itinerary_risks
        WHERE trip_id = :trip_id
          AND expected_offline_minutes IS NOT NULL
          AND expected_offline_minutes > 0
        ORDER BY created_at ASC
        """
    )

    with get_db_engine().begin() as connection:
        rows = connection.execute(query, {"trip_id": trip_id}).mappings().all()

    return [dict(row) for row in rows]
