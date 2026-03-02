"""Heartbeat persistence helpers.

CURE monitoring uses this table to detect delayed reconnect and trigger escalation.
"""

import uuid

from sqlalchemy import text

from app.extensions import get_db_engine


def insert_heartbeat(payload: dict) -> dict:
    """Store device heartbeat payload sent by mobile clients."""
    # Generate UUID for id if not provided
    if "id" not in payload:
        payload = {**payload, "id": str(uuid.uuid4())}
    
    query = text(
        """
        INSERT INTO heartbeats (
            id,
            user_id,
            trip_id,
            timestamp,
            gps_lat,
            gps_lng,
            accuracy_meters,
            battery_percent,
            network_status,
            offline_minutes,
            source,
            emergency_phone
        )
        VALUES (
            :id,
            :user_id,
            :trip_id,
            :timestamp,
            :gps_lat,
            :gps_lng,
            :accuracy_meters,
            :battery_percent,
            :network_status,
            :offline_minutes,
            :source,
            :emergency_phone
        )
        RETURNING *
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(query, payload).mappings().first()

    return dict(row) if row else {}


def list_recent_heartbeats(user_id: str, limit: int = 50) -> list[dict]:
    """Retrieve latest heartbeats for anomaly detection tasks."""
    query = text(
        """
        SELECT *
        FROM heartbeats
        WHERE user_id = :user_id
        ORDER BY timestamp DESC
        LIMIT :limit
        """
    )

    with get_db_engine().begin() as connection:
        rows = connection.execute(query, {"user_id": user_id, "limit": limit}).mappings().all()

    return [dict(row) for row in rows]
