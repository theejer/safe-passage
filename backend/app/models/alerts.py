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


def get_latest_trip_stage_alert(user_id: str, trip_id: str) -> dict:
    """Return latest stage alert row (stage_1/2/3 family) for a trip."""
    if not _is_uuid(user_id) or not _is_uuid(trip_id):
        return {}

    query = text(
        """
        SELECT stage, created_at
        FROM alert_events
        WHERE user_id = :user_id
          AND trip_id = :trip_id
          AND stage IN ('stage_1_initial_alert', 'stage_2_escalation', 'stage_3_auto_reconnection')
        ORDER BY created_at DESC
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {
                "user_id": user_id,
                "trip_id": trip_id,
            },
        ).mappings().first()

    return dict(row) if row else {}


def is_stage_1_rearmed(user_id: str, trip_id: str, buffer_minutes: int = 30) -> tuple[bool, str]:
    """Return whether a trip can emit stage_1 again based on alert lifecycle.

    Rules:
    - If latest stage alert is stage_1 or stage_2 -> block stage_1
    - If latest stage alert is stage_3 -> allow only after cooldown buffer
    - If no prior stage alerts -> allow
    """
    try:
        latest = get_latest_trip_stage_alert(user_id, trip_id)
    except Exception:
        return True, "alert-history-unavailable"

    if not latest:
        return True, "no-prior-stage-alert"

    stage = str(latest.get("stage") or "")
    if stage in {"stage_1_initial_alert", "stage_2_escalation"}:
        return False, f"blocked-by-{stage}"

    if stage != "stage_3_auto_reconnection":
        return True, "unrecognized-stage-allow"

    created_at = latest.get("created_at")
    if not created_at:
        return True, "rearmed-after-stage-3"

    if isinstance(created_at, datetime):
        created_dt = created_at
    else:
        created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))

    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)
    else:
        created_dt = created_dt.astimezone(timezone.utc)

    cooldown_until = created_dt + timedelta(minutes=max(0, int(buffer_minutes)))
    if datetime.now(timezone.utc) < cooldown_until:
        return False, "buffer-after-stage-3"

    return True, "rearmed-after-stage-3"
