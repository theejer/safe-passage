"""Trip persistence helpers.

Trip routes and monitoring tasks use this module to read/write trip metadata.
"""

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _is_missing_table_error(exc: Exception, table_name: str) -> bool:
    message = str(exc).lower()
    return f"no such table: {table_name}" in message or f'relation "{table_name}" does not exist' in message


def _is_missing_column_error(exc: Exception, column_name: str) -> bool:
    message = str(exc).lower()
    return f"no such column: {column_name}" in message or f'column "{column_name}"' in message


def _ensure_trips_table_for_sqlite() -> None:
    engine = get_db_engine()
    if engine.dialect.name != "sqlite":
        return

    create_table_query = text(
        """
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            trip_planned INTEGER NOT NULL DEFAULT 1,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            heartbeat_enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    with engine.begin() as connection:
        connection.execute(create_table_query)


def create_trip(payload: dict) -> dict:
    """Create a trip record that links a user to planned travel dates."""
    trip_id = str(payload.get("id") or uuid4())
    params = {
        "id": trip_id,
        "user_id": payload.get("user_id"),
        "title": payload.get("title"),
        "trip_planned": payload.get("trip_planned", True),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "heartbeat_enabled": payload.get("heartbeat_enabled", True),
    }

    query_with_flags = text(
        """
        INSERT INTO trips (id, user_id, title, trip_planned, start_date, end_date, heartbeat_enabled)
        VALUES (:id, :user_id, :title, :trip_planned, :start_date, :end_date, :heartbeat_enabled)
        RETURNING *
        """
    )
    query_with_heartbeat = text(
        """
        INSERT INTO trips (id, user_id, title, start_date, end_date, heartbeat_enabled)
        VALUES (:id, :user_id, :title, :start_date, :end_date, :heartbeat_enabled)
        RETURNING *
        """
    )
    query_without_heartbeat = text(
        """
        INSERT INTO trips (id, user_id, title, start_date, end_date)
        VALUES (:id, :user_id, :title, :start_date, :end_date)
        RETURNING *
        """
    )

    engine = get_db_engine()

    def _insert_once():
        with engine.begin() as connection:
            try:
                result = connection.execute(query_with_flags, params)
                return result.mappings().first()
            except (ProgrammingError, OperationalError) as exc:
                if _is_missing_column_error(exc, "trip_planned"):
                    try:
                        result = connection.execute(query_with_heartbeat, params)
                        return result.mappings().first()
                    except (ProgrammingError, OperationalError) as inner_exc:
                        if not _is_missing_column_error(inner_exc, "heartbeat_enabled"):
                            raise
                        result = connection.execute(query_without_heartbeat, params)
                        return result.mappings().first()
                if _is_missing_column_error(exc, "heartbeat_enabled"):
                    result = connection.execute(query_without_heartbeat, params)
                    return result.mappings().first()
                raise

    try:
        row = _insert_once()
    except (ProgrammingError, OperationalError) as exc:
        if not _is_missing_table_error(exc, "trips"):
            raise
        _ensure_trips_table_for_sqlite()
        row = _insert_once()

    fallback = dict(row) if row else {}
    fallback.setdefault("trip_planned", payload.get("trip_planned", True))
    fallback.setdefault("heartbeat_enabled", payload.get("heartbeat_enabled", True))
    return fallback


def list_trips_by_user(user_id: str) -> list[dict]:
    """List all trips for a user to drive itinerary/risk views."""
    if not _is_uuid(user_id):
        return []

    query = text("SELECT * FROM trips WHERE user_id = :user_id ORDER BY start_date DESC")
    try:
        with get_db_engine().begin() as connection:
            result = connection.execute(query, {"user_id": user_id})
            rows = result.mappings().all()
    except (ProgrammingError, OperationalError) as exc:
        if not _is_missing_table_error(exc, "trips"):
            raise
        _ensure_trips_table_for_sqlite()
        with get_db_engine().begin() as connection:
            result = connection.execute(query, {"user_id": user_id})
            rows = result.mappings().all()
    return [dict(row) for row in rows]


def get_trip_by_id(trip_id: str) -> dict:
    """Fetch a trip by id for ownership and monitoring checks."""
    if not _is_uuid(trip_id):
        return {}

    query = text("SELECT * FROM trips WHERE id = :trip_id LIMIT 1")
    try:
        with get_db_engine().begin() as connection:
            result = connection.execute(query, {"trip_id": trip_id})
            row = result.mappings().first()
    except (ProgrammingError, OperationalError) as exc:
        if not _is_missing_table_error(exc, "trips"):
            raise
        _ensure_trips_table_for_sqlite()
        with get_db_engine().begin() as connection:
            result = connection.execute(query, {"trip_id": trip_id})
            row = result.mappings().first()
    return dict(row) if row else {}


def delete_trip_by_id(trip_id: str) -> bool:
    """Delete trip and dependent trip-scoped records."""
    if not _is_uuid(trip_id):
        return False

    engine = get_db_engine()
    related_trip_tables = [
        "itineraries",
        "itinerary_risks",
        "heartbeats",
        "alerts",
        "traveler_status",
        "monitoring_expectations",
    ]

    try:
        with engine.begin() as connection:
            for table_name in related_trip_tables:
                try:
                    connection.execute(
                        text(f"DELETE FROM {table_name} WHERE trip_id = :trip_id"),
                        {"trip_id": trip_id},
                    )
                except (ProgrammingError, OperationalError) as exc:
                    if _is_missing_table_error(exc, table_name) or _is_missing_column_error(exc, "trip_id"):
                        continue
                    raise

            result = connection.execute(text("DELETE FROM trips WHERE id = :trip_id"), {"trip_id": trip_id})
            return (result.rowcount or 0) > 0
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc, "trips"):
            _ensure_trips_table_for_sqlite()
            return False
        raise


def get_trip_alert_context(trip_id: str) -> dict:
    """Fetch minimal joined trip context for emergency alerts."""
    if not _is_uuid(trip_id):
        return {}

    query = text(
        """
        SELECT
            t.id,
            t.user_id,
            t.title,
            t.start_date,
            t.end_date,
            t.destination_country,
            u.full_name AS traveler_name
        FROM trips t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = :trip_id
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(query, {"trip_id": trip_id}).mappings().first()

    return dict(row) if row else {}


def list_active_heartbeat_trips(today_iso_date: str) -> list[dict]:
    """List trips currently active and opted into heartbeat monitoring."""
    query_with_flags = text(
        """
        SELECT *
        FROM trips
        WHERE heartbeat_enabled = TRUE
          AND trip_planned = TRUE
          AND (
                (start_date <= :today_iso_date AND end_date >= :today_iso_date)
                OR EXISTS (
                    SELECT 1
                    FROM traveler_status ts
                    WHERE ts.trip_id = trips.id
                      AND ts.monitoring_state <> 'resolved'
                )
          )
        """
    )
    query_with_flags_no_status = text(
        """
        SELECT *
        FROM trips
        WHERE heartbeat_enabled = TRUE
          AND trip_planned = TRUE
          AND start_date <= :today_iso_date
          AND end_date >= :today_iso_date
        """
    )
    query_with_heartbeat = text(
        """
        SELECT *
        FROM trips
        WHERE heartbeat_enabled = TRUE
          AND start_date <= :today_iso_date
          AND end_date >= :today_iso_date
        """
    )
    query_without_heartbeat = text(
        """
        SELECT *
        FROM trips
        WHERE start_date <= :today_iso_date
          AND end_date >= :today_iso_date
        """
    )
    with get_db_engine().begin() as connection:
        try:
            result = connection.execute(query_with_flags, {"today_iso_date": today_iso_date})
        except (ProgrammingError, OperationalError) as exc:
            if _is_missing_table_error(exc, "trips"):
                _ensure_trips_table_for_sqlite()
                result = connection.execute(query_without_heartbeat, {"today_iso_date": today_iso_date})
            elif _is_missing_table_error(exc, "traveler_status"):
                result = connection.execute(query_with_flags_no_status, {"today_iso_date": today_iso_date})
            elif _is_missing_column_error(exc, "trip_planned"):
                result = connection.execute(query_with_heartbeat, {"today_iso_date": today_iso_date})
            elif not _is_missing_column_error(exc, "heartbeat_enabled"):
                raise
            else:
                result = connection.execute(query_without_heartbeat, {"today_iso_date": today_iso_date})
        rows = result.mappings().all()
    output: list[dict] = []
    for row in rows:
        row_dict = dict(row)
        row_dict.setdefault("trip_planned", True)
        row_dict.setdefault("heartbeat_enabled", True)
        output.append(row_dict)
    return output
