"""Trip persistence helpers.

Trip routes and monitoring tasks use this module to read/write trip metadata.
"""

from uuid import UUID

from sqlalchemy import text

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def create_trip(payload: dict) -> dict:
    """Create a trip record that links a user to planned travel dates."""
    query = text(
        """
        INSERT INTO trips (user_id, title, start_date, end_date, heartbeat_enabled)
        VALUES (:user_id, :title, :start_date, :end_date, :heartbeat_enabled)
        RETURNING *
        """
    )
    with get_db_engine().begin() as connection:
        result = connection.execute(
            query,
            {
                "user_id": payload.get("user_id"),
                "title": payload.get("title"),
                "start_date": payload.get("start_date"),
                "end_date": payload.get("end_date"),
                "heartbeat_enabled": payload.get("heartbeat_enabled", True),
            },
        )
        row = result.mappings().first()
    return dict(row) if row else {}


def list_trips_by_user(user_id: str) -> list[dict]:
    """List all trips for a user to drive itinerary/risk views."""
    if not _is_uuid(user_id):
        return []

    query = text("SELECT * FROM trips WHERE user_id = :user_id ORDER BY start_date DESC")
    with get_db_engine().begin() as connection:
        result = connection.execute(query, {"user_id": user_id})
        rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_trip_by_id(trip_id: str) -> dict:
    """Fetch a trip by id for ownership and monitoring checks."""
    if not _is_uuid(trip_id):
        return {}

    query = text("SELECT * FROM trips WHERE id = :trip_id LIMIT 1")
    with get_db_engine().begin() as connection:
        result = connection.execute(query, {"trip_id": trip_id})
        row = result.mappings().first()
    return dict(row) if row else {}


def list_active_heartbeat_trips(today_iso_date: str) -> list[dict]:
    """List trips currently active and opted into heartbeat monitoring."""
    query = text(
        """
        SELECT *
        FROM trips
        WHERE heartbeat_enabled = TRUE
          AND start_date <= :today_iso_date
          AND end_date >= :today_iso_date
        """
    )
    with get_db_engine().begin() as connection:
        result = connection.execute(query, {"today_iso_date": today_iso_date})
        rows = result.mappings().all()
    return [dict(row) for row in rows]
