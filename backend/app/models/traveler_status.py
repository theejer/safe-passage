"""Traveler monitoring state persistence helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text

from app.extensions import get_db_engine


ALLOWED_UPDATE_FIELDS = {
    "last_seen_at",
    "last_seen_lat",
    "last_seen_lng",
    "last_battery_percent",
    "last_network_status",
    "location_risk",
    "connectivity_risk",
    "current_segment_id",
    "current_stage",
    "monitoring_state",
    "last_stage_change_at",
    "last_evaluated_at",
}


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def get_status_for_trip(user_id: str, trip_id: str) -> dict:
    """Return latest traveler status row for user/trip."""
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return {}

    query = text(
        """
        SELECT *
        FROM traveler_status
        WHERE user_id = :user_id
          AND trip_id = :trip_id
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(query, {"user_id": user_id, "trip_id": trip_id}).mappings().first()

    return dict(row) if row else {}


def upsert_status(payload: dict) -> dict:
    """Insert or update traveler status row keyed by user_id + trip_id."""
    user_id = payload.get("user_id")
    trip_id = payload.get("trip_id")
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return {}

    query = text(
        """
        INSERT INTO traveler_status (
            id,
            user_id,
            trip_id,
            last_seen_at,
            last_seen_lat,
            last_seen_lng,
            last_battery_percent,
            last_network_status,
            location_risk,
            connectivity_risk,
            current_stage,
            monitoring_state,
            last_stage_change_at,
            last_evaluated_at
        )
        VALUES (
            :id,
            :user_id,
            :trip_id,
            :last_seen_at,
            :last_seen_lat,
            :last_seen_lng,
            :last_battery_percent,
            :last_network_status,
            :location_risk,
            :connectivity_risk,
            :current_stage,
            :monitoring_state,
            :last_stage_change_at,
            :last_evaluated_at
        )
        ON CONFLICT (user_id, trip_id)
        DO UPDATE SET
            last_seen_at = EXCLUDED.last_seen_at,
            last_seen_lat = EXCLUDED.last_seen_lat,
            last_seen_lng = EXCLUDED.last_seen_lng,
            last_battery_percent = EXCLUDED.last_battery_percent,
            last_network_status = EXCLUDED.last_network_status,
            location_risk = EXCLUDED.location_risk,
            connectivity_risk = EXCLUDED.connectivity_risk,
            current_stage = EXCLUDED.current_stage,
            monitoring_state = EXCLUDED.monitoring_state,
            last_stage_change_at = EXCLUDED.last_stage_change_at,
            last_evaluated_at = EXCLUDED.last_evaluated_at,
            updated_at = NOW()
        RETURNING *
        """
    )

    params = {
        "id": payload.get("id"),
        "user_id": user_id,
        "trip_id": trip_id,
        "last_seen_at": payload.get("last_seen_at"),
        "last_seen_lat": payload.get("last_seen_lat"),
        "last_seen_lng": payload.get("last_seen_lng"),
        "last_battery_percent": payload.get("last_battery_percent"),
        "last_network_status": payload.get("last_network_status"),
        "location_risk": payload.get("location_risk"),
        "connectivity_risk": payload.get("connectivity_risk"),
        "current_stage": payload.get("current_stage", "none"),
        "monitoring_state": payload.get("monitoring_state", "active"),
        "last_stage_change_at": payload.get("last_stage_change_at"),
        "last_evaluated_at": payload.get("last_evaluated_at"),
    }

    with get_db_engine().begin() as connection:
        row = connection.execute(query, params).mappings().first()

    return dict(row) if row else {}


def update_status(user_id: str, trip_id: str, updates: dict) -> dict:
    """Apply partial update to traveler status."""
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return {}

    filtered_updates = {key: value for key, value in updates.items() if key in ALLOWED_UPDATE_FIELDS}
    if not filtered_updates:
        return get_status_for_trip(user_id, trip_id)

    set_clause = ", ".join([f"{key} = :{key}" for key in filtered_updates] + ["updated_at = NOW()"])
    query = text(
        f"""
        UPDATE traveler_status
        SET {set_clause}
        WHERE user_id = :user_id
          AND trip_id = :trip_id
        RETURNING *
        """
    )

    params = {**filtered_updates, "user_id": user_id, "trip_id": trip_id}
    with get_db_engine().begin() as connection:
        row = connection.execute(query, params).mappings().first()

    return dict(row) if row else {}


def list_open_statuses() -> list[dict]:
    """List statuses still being monitored for staged alerts."""
    query = text(
        """
        SELECT *
        FROM traveler_status
        WHERE monitoring_state <> 'resolved'
        """
    )

    with get_db_engine().begin() as connection:
        rows = connection.execute(query).mappings().all()

    return [dict(row) for row in rows]


def list_open_stage_1_trip_ids_for_user(user_id: str) -> list[str]:
    """Return open stage-1 trip ids for a user, newest stage-change first."""
    if not _is_uuid(user_id):
        return []

    query = text(
        """
        SELECT trip_id
        FROM traveler_status
        WHERE user_id = :user_id
          AND current_stage = 'stage_1_initial_alert'
          AND monitoring_state <> 'resolved'
        ORDER BY last_stage_change_at DESC NULLS LAST, updated_at DESC
        """
    )

    with get_db_engine().begin() as connection:
        rows = connection.execute(query, {"user_id": user_id}).mappings().all()

    return [str(row.get("trip_id")) for row in rows if row.get("trip_id")]
