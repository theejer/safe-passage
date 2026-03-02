"""Alert event persistence wrappers used by watchdog escalation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import text

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def create_alert_event(payload: dict) -> dict:
    """Insert alert event row and return created record."""
    query = text(
        """
        INSERT INTO alert_events (
            id,
            user_id,
            trip_id,
            stage,
            message,
            channels,
            recipients,
            escalation_context
        )
        VALUES (
            :id,
            :user_id,
            :trip_id,
            :stage,
            :message,
            CAST(:channels AS jsonb),
            CAST(:recipients AS jsonb),
            CAST(:escalation_context AS jsonb)
        )
        RETURNING *
        """
    )

    import json

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {
                "id": payload.get("id"),
                "user_id": payload.get("user_id"),
                "trip_id": payload.get("trip_id"),
                "stage": payload.get("stage"),
                "message": payload.get("message"),
                "channels": json.dumps(payload.get("channels") or []),
                "recipients": json.dumps(payload.get("recipients") or []),
                "escalation_context": json.dumps(payload.get("escalation_context") or {}),
            },
        ).mappings().first()

    return dict(row) if row else {}


def has_recent_stage_alert(user_id: str, trip_id: str, stage: str, within_minutes: int) -> bool:
    """Check if same stage alert already emitted recently to avoid spam."""
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return False

    since = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    query = text(
        """
        SELECT id
        FROM alert_events
        WHERE user_id = :user_id
          AND trip_id = :trip_id
          AND stage = :stage
          AND created_at >= :since
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {
                "user_id": user_id,
                "trip_id": trip_id,
                "stage": stage,
                "since": since,
            },
        ).mappings().first()

    return bool(row)


def has_stage_1_confirmation(user_id: str, trip_id: str, since: datetime | None = None) -> bool:
    """Return whether emergency contact confirmed unreachability after stage-1."""
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return False

    query = text(
        """
        SELECT id
        FROM alert_events
        WHERE user_id = :user_id
          AND trip_id = :trip_id
          AND stage = 'stage_1_contact_confirmation'
          AND (:since IS NULL OR created_at >= :since)
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {
                "user_id": user_id,
                "trip_id": trip_id,
                "since": since,
            },
        ).mappings().first()

    return bool(row)
