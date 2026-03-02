"""Monitoring expectation persistence helpers.

Stores dynamic expected-offline windows used by watchdog thresholding.
"""

from __future__ import annotations

from sqlalchemy import text

from app.extensions import get_db_engine


def upsert_monitoring_expectation(
    trip_id: str,
    expected_offline_minutes: int,
    threshold_multiplier: float,
    location_name: str = "dynamic_window",
) -> dict:
    """Upsert one expectation row per trip/location_name."""
    update_query = text(
        """
        UPDATE monitoring_expectations
        SET expected_offline_minutes = :expected_offline_minutes,
            threshold_multiplier = :threshold_multiplier,
            created_at = NOW()
        WHERE trip_id = :trip_id
          AND location_name = :location_name
        RETURNING *
        """
    )

    insert_query = text(
        """
        INSERT INTO monitoring_expectations (
            id,
            trip_id,
            location_name,
            expected_offline_minutes,
            threshold_multiplier
        )
        VALUES (
            gen_random_uuid(),
            :trip_id,
            :location_name,
            :expected_offline_minutes,
            :threshold_multiplier
        )
        RETURNING *
        """
    )

    params = {
        "trip_id": trip_id,
        "location_name": location_name,
        "expected_offline_minutes": int(expected_offline_minutes),
        "threshold_multiplier": float(threshold_multiplier),
    }

    with get_db_engine().begin() as connection:
        updated = connection.execute(update_query, params).mappings().first()
        if updated:
            return dict(updated)
        created = connection.execute(insert_query, params).mappings().first()

    return dict(created) if created else {}


def get_latest_monitoring_expectation(trip_id: str, location_name: str = "dynamic_window") -> dict:
    """Return latest expectation row for trip/location_name."""
    query = text(
        """
        SELECT *
        FROM monitoring_expectations
        WHERE trip_id = :trip_id
          AND location_name = :location_name
        ORDER BY created_at DESC
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {
                "trip_id": trip_id,
                "location_name": location_name,
            },
        ).mappings().first()

    return dict(row) if row else {}
