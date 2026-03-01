"""Heartbeat monitoring and staged escalation service.

This service coordinates heartbeat ingest side-effects and watchdog checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.alerts import create_alert_event, has_recent_stage_alert
from app.models.itinerary_segments import list_segments_for_trip
from app.models.traveler_status import get_status_for_trip, list_open_statuses, update_status, upsert_status
from app.models.trips import get_trip_by_id, list_active_heartbeat_trips
from app.models.users import get_user_by_id
from app.services.notifications import send_sms_alert

STAGE_1 = "stage_1_initial_alert"
STAGE_2 = "stage_2_escalation"
STAGE_3 = "stage_3_auto_reconnection"


def _parse_iso(iso_text: str) -> datetime:
    value = iso_text.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _risk_multiplier(connectivity_risk: str, battery_percent: int | None, event_time: datetime) -> float:
    multiplier = 1.0

    if connectivity_risk in {"severe", "remote_no_signal"}:
        multiplier *= 0.65
    elif connectivity_risk in {"high", "rural_weak", "transit_intermittent"}:
        multiplier *= 0.8
    elif connectivity_risk in {"moderate", "semi_urban_patchy"}:
        multiplier *= 0.95

    if battery_percent is not None and battery_percent <= 20:
        multiplier *= 0.85

    hour = event_time.hour
    if hour >= 20 or hour <= 5:
        multiplier *= 0.85

    if event_time.weekday() >= 5:
        multiplier *= 0.9

    return max(0.45, multiplier)


def derive_expected_offline_minutes(trip_id: str) -> int:
    """Resolve expected offline window from itinerary segments.

    Falls back to conservative defaults when no segment exists.
    """
    segments = list_segments_for_trip(trip_id)
    if not segments:
        return 90

    candidate_windows = [
        int(segment.get("expected_offline_minutes", 0))
        for segment in segments
        if segment.get("expected_offline_minutes") is not None
    ]
    candidate_windows = [value for value in candidate_windows if value > 0]
    if not candidate_windows:
        return 90

    return max(15, int(sum(candidate_windows) / len(candidate_windows)))


def _build_recipients(user: dict, emergency_phone: str | None) -> list[dict]:
    recipients: list[dict] = []

    profile_contact = user.get("emergency_contact") if isinstance(user, dict) else None
    if isinstance(profile_contact, dict):
        recipients.append(
            {
                "type": "emergency_contact",
                "name": profile_contact.get("name"),
                "phone": profile_contact.get("phone"),
                "email": profile_contact.get("email"),
            }
        )

    if emergency_phone:
        recipients.append({"type": "runtime_emergency_phone", "phone": emergency_phone})

    deduped: list[dict] = []
    seen = set()
    for recipient in recipients:
        phone = recipient.get("phone")
        if phone and phone in seen:
            continue
        if phone:
            seen.add(phone)
        deduped.append(recipient)

    return deduped


def _send_and_record_stage_alert(
    user_id: str,
    trip_id: str,
    stage: str,
    message: str,
    recipients: list[dict],
    escalation_context: dict | None = None,
) -> dict:
    for recipient in recipients:
        phone = recipient.get("phone")
        if phone:
            send_sms_alert(phone, message)

    payload = {
        "id": str(uuid4()),
        "user_id": user_id,
        "trip_id": trip_id,
        "stage": stage,
        "message": message,
        "channels": ["sms"],
        "recipients": recipients,
        "escalation_context": escalation_context or {},
    }
    return create_alert_event(payload)


def process_heartbeat_ingest(heartbeat_row: dict) -> dict:
    """Update traveler status from ingest and emit stage-3 recovery when needed."""
    user_id = heartbeat_row["user_id"]
    trip_id = heartbeat_row["trip_id"]
    timestamp = heartbeat_row["timestamp"]
    prior = get_status_for_trip(user_id, trip_id)
    prior_stage = prior.get("current_stage", "none")

    status = upsert_status(
        {
            "id": prior.get("id") or str(uuid4()),
            "user_id": user_id,
            "trip_id": trip_id,
            "last_seen_at": timestamp,
            "last_seen_lat": heartbeat_row.get("gps_lat"),
            "last_seen_lng": heartbeat_row.get("gps_lng"),
            "last_battery_percent": heartbeat_row.get("battery_percent"),
            "last_network_status": heartbeat_row.get("network_status"),
            "monitoring_state": "active",
            "current_stage": "none" if prior_stage == "none" else prior_stage,
            "last_stage_change_at": timestamp,
        }
    )

    if prior_stage in {STAGE_1, STAGE_2} and heartbeat_row.get("network_status") == "online":
        user = get_user_by_id(user_id)
        recipients = _build_recipients(user, heartbeat_row.get("emergency_phone"))
        _send_and_record_stage_alert(
            user_id=user_id,
            trip_id=trip_id,
            stage=STAGE_3,
            message=f"SafePassage Update: traveler is back online for trip {trip_id}.",
            recipients=recipients,
            escalation_context={"recovery": True},
        )
        update_status(
            user_id,
            trip_id,
            {
                "current_stage": STAGE_3,
                "monitoring_state": "resolved",
                "last_stage_change_at": timestamp,
            },
        )

    return status


def evaluate_status_for_alert(status: dict, now_utc: datetime) -> dict:
    """Evaluate one traveler status row and emit stage alerts when thresholds cross."""
    user_id = status.get("user_id", "")
    trip_id = status.get("trip_id", "")
    if not user_id or not trip_id:
        return {"trip_id": trip_id, "status": "skipped-missing-keys"}

    trip = get_trip_by_id(trip_id)
    if not trip or not trip.get("heartbeat_enabled", True):
        return {"trip_id": trip_id, "status": "skipped-heartbeat-disabled"}

    last_seen_at = status.get("last_seen_at")
    if not last_seen_at:
        return {"trip_id": trip_id, "status": "skipped-no-last-seen"}

    last_seen_dt = _parse_iso(last_seen_at)
    offline_duration_minutes = max(0, int((now_utc - last_seen_dt).total_seconds() // 60))

    expected = derive_expected_offline_minutes(trip_id)
    connectivity_risk = status.get("connectivity_risk", "moderate")
    battery_percent = status.get("last_battery_percent")
    multiplier = _risk_multiplier(connectivity_risk, battery_percent, now_utc)

    adjusted_expected = max(15, int(expected * multiplier))
    stage_1_threshold = adjusted_expected
    stage_2_threshold = max(int(adjusted_expected * 1.8), adjusted_expected + 30)

    trigger_stage = "none"
    if offline_duration_minutes >= stage_2_threshold:
        trigger_stage = STAGE_2
    elif offline_duration_minutes >= stage_1_threshold:
        trigger_stage = STAGE_1

    current_stage = status.get("current_stage", "none")
    if trigger_stage == "none" or trigger_stage == current_stage:
        return {
            "trip_id": trip_id,
            "status": "within-window" if trigger_stage == "none" else "unchanged-stage",
            "offline_duration_minutes": offline_duration_minutes,
            "expected_offline_minutes": adjusted_expected,
        }

    dedupe_window = 30 if trigger_stage == STAGE_1 else 60
    if has_recent_stage_alert(user_id, trip_id, trigger_stage, dedupe_window):
        return {"trip_id": trip_id, "status": "deduped", "trigger_stage": trigger_stage}

    user = get_user_by_id(user_id)
    recipients = _build_recipients(user, status.get("emergency_phone"))

    message = (
        f"SafePassage Alert: traveler offline for {offline_duration_minutes} minutes on trip {trip_id}. "
        f"Expected window was {adjusted_expected} minutes."
    )
    escalation_context = {
        "threshold_rule": "offline > expected * multiplier",
        "location_risk": status.get("location_risk", "moderate"),
        "connectivity_risk": connectivity_risk,
        "battery_percent": battery_percent,
        "last_seen_lat": status.get("last_seen_lat"),
        "last_seen_lng": status.get("last_seen_lng"),
    }
    _send_and_record_stage_alert(
        user_id=user_id,
        trip_id=trip_id,
        stage=trigger_stage,
        message=message,
        recipients=recipients,
        escalation_context=escalation_context,
    )

    update_status(
        user_id,
        trip_id,
        {
            "current_stage": trigger_stage,
            "monitoring_state": "alerted",
            "last_stage_change_at": now_utc.isoformat(),
            "last_evaluated_at": now_utc.isoformat(),
        },
    )

    return {
        "trip_id": trip_id,
        "status": "alerted",
        "trigger_stage": trigger_stage,
        "offline_duration_minutes": offline_duration_minutes,
        "expected_offline_minutes": adjusted_expected,
    }


def run_watchdog_cycle(now_utc: datetime | None = None) -> dict:
    """Run one full watchdog pass across active heartbeat-monitored trips."""
    now = now_utc or datetime.now(timezone.utc)
    today = now.date().isoformat()

    active_trips = list_active_heartbeat_trips(today)
    open_statuses = list_open_statuses()
    statuses_by_trip = {item.get("trip_id"): item for item in open_statuses}

    results: list[dict] = []
    for trip in active_trips:
        trip_id = trip.get("id")
        if not trip_id:
            continue
        status = statuses_by_trip.get(trip_id)
        if not status:
            results.append({"trip_id": trip_id, "status": "no-status"})
            continue
        results.append(evaluate_status_for_alert(status, now))

    return {
        "evaluated_at": now.isoformat(),
        "active_trip_count": len(active_trips),
        "result_count": len(results),
        "results": results,
    }
