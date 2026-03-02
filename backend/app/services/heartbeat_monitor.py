"""Heartbeat monitoring and staged escalation service.

This service coordinates heartbeat ingest side-effects and watchdog checks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from flask import current_app, has_app_context

from app.models.alerts import create_alert_event, has_recent_stage_alert, has_stage_1_confirmation
from app.models.itinerary_segments import list_segments_for_trip
from app.models.traveler_status import get_status_for_trip, list_open_statuses, update_status, upsert_status
from app.models.trips import get_trip_alert_context, get_trip_by_id, list_active_heartbeat_trips
from app.models.users import get_user_by_id
from app.services.notifications import send_telegram_alert

STAGE_1 = "stage_1_initial_alert"
STAGE_2 = "stage_2_escalation"
STAGE_3 = "stage_3_auto_reconnection"
STAGE_1_CONTACT_CONFIRMATION = "stage_1_contact_confirmation"

logger = logging.getLogger("watchdog")

_ISO2_COUNTRY_NAMES = {
    "IN": "India",
    "SG": "Singapore",
    "MY": "Malaysia",
    "TH": "Thailand",
    "ID": "Indonesia",
    "VN": "Vietnam",
    "PH": "Philippines",
    "NP": "Nepal",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "US": "United States",
    "GB": "United Kingdom",
    "AU": "Australia",
    "CA": "Canada",
    "AE": "United Arab Emirates",
}


def _resolve_trip_alert_context(trip_id: str, trip: dict | None = None, user: dict | None = None) -> dict:
    context = get_trip_alert_context(trip_id)
    if context:
        return context

    fallback_trip = trip or {}
    fallback_user = user or {}
    return {
        "id": trip_id,
        "user_id": fallback_trip.get("user_id") if isinstance(fallback_trip, dict) else None,
        "title": fallback_trip.get("title") if isinstance(fallback_trip, dict) else None,
        "start_date": fallback_trip.get("start_date") if isinstance(fallback_trip, dict) else None,
        "end_date": fallback_trip.get("end_date") if isinstance(fallback_trip, dict) else None,
        "destination_country": (
            fallback_trip.get("destination_country")
            if isinstance(fallback_trip, dict)
            else None
        ),
        "traveler_name": fallback_user.get("full_name") if isinstance(fallback_user, dict) else None,
    }


def _format_trip_window(context: dict) -> str:
    start_date = context.get("start_date")
    end_date = context.get("end_date")
    country = context.get("destination_country") or context.get("country")

    display_country = None
    if isinstance(country, str):
        normalized_country = country.strip()
        if len(normalized_country) == 2 and normalized_country.isalpha():
            display_country = _ISO2_COUNTRY_NAMES.get(normalized_country.upper(), normalized_country.upper())
        elif normalized_country:
            display_country = normalized_country

    window_parts = []
    if start_date and end_date:
        window_parts.append(f"{start_date} to {end_date}")
    if display_country:
        window_parts.append(display_country)
    return " | ".join(window_parts) if window_parts else "current itinerary"


def _is_force_stage_1_test_mode() -> bool:
    if not has_app_context():
        return False
    return bool(current_app.config.get("HEARTBEAT_FORCE_STAGE_1_TEST_MODE", False))


def _parse_iso(iso_text: str | datetime) -> datetime:
    if isinstance(iso_text, datetime):
        dt = iso_text
    else:
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
        telegram_chat_id = profile_contact.get("telegram_chat_id")
        telegram_bot_active = bool(profile_contact.get("telegram_bot_active"))
        if telegram_chat_id and telegram_bot_active:
            recipients.append(
                {
                    "type": "emergency_contact",
                    "name": profile_contact.get("name"),
                    "phone": profile_contact.get("phone"),
                    "telegram_chat_id": str(telegram_chat_id),
                    "telegram_bot_active": True,
                }
            )

    if emergency_phone:
        recipients.append({"type": "runtime_emergency_phone", "phone": emergency_phone, "delivery": "unlinked"})

    deduped: list[dict] = []
    seen = set()
    for recipient in recipients:
        chat_id = recipient.get("telegram_chat_id")
        key = chat_id or recipient.get("phone")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(recipient)

    return deduped


def _build_stage_1_message(
    alert_context: dict,
    force_stage_1_test_mode: bool,
) -> str:
    traveler_name = alert_context.get("traveler_name") or "the traveler"
    trip_window = _format_trip_window(alert_context)
    prefix = "[TEST MODE] " if force_stage_1_test_mode else ""
    return (
        f"{prefix}URGENT: SafePassage has temporarily lost contact with {traveler_name}. "
        f"Trip window: {trip_window}. "
        "Can you contact them now? Reply YES if reachable, or NO if not reachable."
    )


def _bootstrap_missing_status_with_stage_1(trip: dict, now_utc: datetime) -> dict:
    """Create stage-1 alert when active heartbeat trip has no traveler_status row."""
    trip_id = str(trip.get("id") or "")
    user_id = str(trip.get("user_id") or "")
    if not trip_id or not user_id:
        return {"trip_id": trip_id, "status": "skipped-missing-keys"}

    if has_recent_stage_alert(user_id, trip_id, STAGE_1, within_minutes=30):
        return {
            "trip_id": trip_id,
            "status": "deduped",
            "trigger_stage": STAGE_1,
            "reason": "missing-status-row",
        }

    user = get_user_by_id(user_id)
    recipients = _build_recipients(user, None)
    force_stage_1_test_mode = _is_force_stage_1_test_mode()
    alert_context = _resolve_trip_alert_context(trip_id, trip=trip, user=user)
    message = _build_stage_1_message(alert_context, force_stage_1_test_mode)
    escalation_context = {
        "threshold_rule": "missing-status-row-bootstrap",
        "location_risk": "unknown",
        "connectivity_risk": "unknown",
        "battery_percent": None,
        "last_seen_lat": None,
        "last_seen_lng": None,
        "test_mode": force_stage_1_test_mode,
    }
    created_alert_event = _send_and_record_stage_alert(
        user_id=user_id,
        trip_id=trip_id,
        stage=STAGE_1,
        message=message,
        recipients=recipients,
        escalation_context=escalation_context,
    )

    upsert_status(
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "trip_id": trip_id,
            "last_seen_at": None,
            "last_seen_lat": None,
            "last_seen_lng": None,
            "last_battery_percent": None,
            "last_network_status": "unknown",
            "location_risk": "unknown",
            "connectivity_risk": "unknown",
            "monitoring_state": "alerted",
            "current_stage": STAGE_1,
            "last_stage_change_at": now_utc.isoformat(),
            "last_evaluated_at": now_utc.isoformat(),
        }
    )

    return {
        "trip_id": trip_id,
        "status": "alerted",
        "trigger_stage": STAGE_1,
        "offline_duration_minutes": 0,
        "expected_offline_minutes": 0,
        "alert_event": created_alert_event,
        "reason": "missing-status-row",
    }


def _send_and_record_stage_alert(
    user_id: str,
    trip_id: str,
    stage: str,
    message: str,
    recipients: list[dict],
    escalation_context: dict | None = None,
) -> dict:
    bot_token = ""
    if has_app_context():
        bot_token = current_app.config.get("TELEGRAM_BOT_TOKEN", "")

    delivered_channels: set[str] = set()
    for recipient in recipients:
        chat_id = recipient.get("telegram_chat_id")
        if chat_id:
            result = send_telegram_alert(str(chat_id), message, bot_token=bot_token)
            if result.get("queued"):
                delivered_channels.add("telegram")

    payload = {
        "id": str(uuid4()),
        "user_id": user_id,
        "trip_id": trip_id,
        "stage": stage,
        "message": message,
        "channels": sorted(delivered_channels),
        "recipients": recipients,
        "escalation_context": escalation_context or {},
    }
    created_event = create_alert_event(payload)
    logger.info(
        "[watchdog] alert_created stage=%s alert_id=%s user_id=%s trip_id=%s channels=%s recipients=%s",
        stage,
        created_event.get("id") if isinstance(created_event, dict) else None,
        user_id,
        trip_id,
        payload.get("channels") or [],
        len(recipients),
    )
    return created_event


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
        alert_context = _resolve_trip_alert_context(trip_id, user=user)
        _send_and_record_stage_alert(
            user_id=user_id,
            trip_id=trip_id,
            stage=STAGE_3,
            message=(
                f"SafePassage update: {alert_context.get('traveler_name') or 'The traveler'} "
                f"is back online ({_format_trip_window(alert_context)})."
            ),
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


def apply_stage_1_contact_response(
    user_id: str,
    trip_id: str,
    can_contact: bool,
    confirmed_by: str,
    source: str = "telegram",
    note: str | None = None,
) -> dict:
    """Apply emergency-contact YES/NO response for a stage-1 alert."""
    status = get_status_for_trip(user_id, trip_id)
    if not status:
        return {"status": "status-not-found", "user_id": user_id, "trip_id": trip_id}

    if status.get("current_stage") != STAGE_1:
        return {
            "status": "ignored-stage-mismatch",
            "user_id": user_id,
            "trip_id": trip_id,
            "current_stage": status.get("current_stage", "none"),
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    user = get_user_by_id(user_id)
    recipients = _build_recipients(user, status.get("emergency_phone"))
    alert_context = _resolve_trip_alert_context(trip_id, user=user)

    if can_contact:
        message = (
            f"SafePassage update: emergency contact confirmed "
            f"{alert_context.get('traveler_name') or 'the traveler'} is reachable "
            f"({_format_trip_window(alert_context)})."
        )
        created_alert_event = _send_and_record_stage_alert(
            user_id=user_id,
            trip_id=trip_id,
            stage=STAGE_3,
            message=message,
            recipients=recipients,
            escalation_context={
                "contact_response": "yes",
                "confirmed_by": confirmed_by,
                "source": source,
                "note": note or "",
            },
        )
        update_status(
            user_id,
            trip_id,
            {
                "current_stage": STAGE_3,
                "monitoring_state": "resolved",
                "last_stage_change_at": now_iso,
                "last_evaluated_at": now_iso,
            },
        )
        return {
            "status": "deescalated",
            "stage": STAGE_3,
            "alert_event": created_alert_event,
        }

    record_stage_1_contact_confirmation(
        user_id=user_id,
        trip_id=trip_id,
        confirmed_by=confirmed_by,
        note=note,
    )

    if has_recent_stage_alert(user_id, trip_id, STAGE_2, within_minutes=60):
        return {
            "status": "deduped",
            "stage": STAGE_2,
            "trip_id": trip_id,
            "user_id": user_id,
        }

    message = (
        "URGENT: Emergency contact confirmed the traveler remains unreachable. "
        f"Escalating to Stage 2 ({_format_trip_window(alert_context)})."
    )
    created_alert_event = _send_and_record_stage_alert(
        user_id=user_id,
        trip_id=trip_id,
        stage=STAGE_2,
        message=message,
        recipients=recipients,
        escalation_context={
            "contact_response": "no",
            "confirmed_by": confirmed_by,
            "source": source,
            "note": note or "",
        },
    )
    update_status(
        user_id,
        trip_id,
        {
            "current_stage": STAGE_2,
            "monitoring_state": "alerted",
            "last_stage_change_at": now_iso,
            "last_evaluated_at": now_iso,
        },
    )
    return {
        "status": "escalated",
        "stage": STAGE_2,
        "alert_event": created_alert_event,
    }


def record_stage_1_contact_confirmation(
    user_id: str,
    trip_id: str,
    confirmed_by: str,
    note: str | None = None,
) -> dict:
    """Persist explicit emergency-contact confirmation required before stage-2 escalation."""
    status = get_status_for_trip(user_id, trip_id)
    if not status:
        return {"status": "status-not-found", "user_id": user_id, "trip_id": trip_id}

    if status.get("current_stage") != STAGE_1:
        return {
            "status": "ignored-stage-mismatch",
            "user_id": user_id,
            "trip_id": trip_id,
            "current_stage": status.get("current_stage", "none"),
        }

    if has_recent_stage_alert(user_id, trip_id, STAGE_1_CONTACT_CONFIRMATION, within_minutes=60):
        return {
            "status": "deduped",
            "user_id": user_id,
            "trip_id": trip_id,
            "stage": STAGE_1_CONTACT_CONFIRMATION,
        }

    message = (
        f"SafePassage Confirmation: emergency contact confirmed traveler remains unreachable for trip {trip_id}."
    )
    confirmation_event = create_alert_event(
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "trip_id": trip_id,
            "stage": STAGE_1_CONTACT_CONFIRMATION,
            "message": message,
            "channels": ["manual_confirmation"],
            "recipients": [{"type": "operator", "confirmed_by": confirmed_by}],
            "escalation_context": {
                "confirmed_unreachable": True,
                "confirmed_by": confirmed_by,
                "note": note or "",
            },
        }
    )
    update_status(
        user_id,
        trip_id,
        {
            "monitoring_state": "contact_confirmed_unreachable",
            "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {
        "status": "confirmed",
        "stage": STAGE_1_CONTACT_CONFIRMATION,
        "confirmation_event": confirmation_event,
    }


def evaluate_status_for_alert(status: dict, now_utc: datetime) -> dict:
    """Evaluate one traveler status row and emit stage alerts when thresholds cross."""
    user_id = status.get("user_id", "")
    trip_id = status.get("trip_id", "")
    if not user_id or not trip_id:
        return {"trip_id": trip_id, "status": "skipped-missing-keys"}

    trip = get_trip_by_id(trip_id)
    if not trip or not trip.get("heartbeat_enabled", True):
        return {"trip_id": trip_id, "status": "skipped-heartbeat-disabled"}

    force_stage_1_test_mode = _is_force_stage_1_test_mode()

    last_seen_at = status.get("last_seen_at")
    if not last_seen_at and not force_stage_1_test_mode:
        return {"trip_id": trip_id, "status": "skipped-no-last-seen"}

    offline_duration_minutes = 0
    if last_seen_at:
        last_seen_dt = _parse_iso(last_seen_at)
        offline_duration_minutes = max(0, int((now_utc - last_seen_dt).total_seconds() // 60))

    connectivity_risk = status.get("connectivity_risk", "moderate")
    battery_percent = status.get("last_battery_percent")
    adjusted_expected = 0
    stage_1_threshold = 0
    stage_2_threshold = 0

    if not force_stage_1_test_mode:
        expected = derive_expected_offline_minutes(trip_id)
        multiplier = _risk_multiplier(connectivity_risk, battery_percent, now_utc)
        adjusted_expected = max(15, int(expected * multiplier))
        stage_1_threshold = adjusted_expected
        stage_2_threshold = max(int(adjusted_expected * 1.8), adjusted_expected + 30)

    current_stage = status.get("current_stage", "none")
    trigger_stage = "none"
    if force_stage_1_test_mode:
        trigger_stage = STAGE_1
    else:
        if current_stage in {"none", ""}:
            if offline_duration_minutes >= stage_1_threshold:
                trigger_stage = STAGE_1
        elif current_stage == STAGE_1 and offline_duration_minutes >= stage_2_threshold:
            since = None
            last_stage_change_at = status.get("last_stage_change_at")
            if last_stage_change_at:
                since = _parse_iso(last_stage_change_at)

            if has_stage_1_confirmation(user_id, trip_id, since=since):
                trigger_stage = STAGE_2
            else:
                return {
                    "trip_id": trip_id,
                    "status": "awaiting-contact-confirmation",
                    "current_stage": current_stage,
                    "offline_duration_minutes": offline_duration_minutes,
                    "expected_offline_minutes": adjusted_expected,
                    "requires_confirmation": True,
                }

    if trigger_stage == "none":
        return {
            "trip_id": trip_id,
            "status": "within-window",
            "offline_duration_minutes": offline_duration_minutes,
            "expected_offline_minutes": adjusted_expected,
        }

    if trigger_stage == current_stage and not (force_stage_1_test_mode and trigger_stage == STAGE_1):
        return {
            "trip_id": trip_id,
            "status": "unchanged-stage",
            "offline_duration_minutes": offline_duration_minutes,
            "expected_offline_minutes": adjusted_expected,
        }

    dedupe_window = 30 if trigger_stage == STAGE_1 else 60
    if has_recent_stage_alert(user_id, trip_id, trigger_stage, dedupe_window):
        return {"trip_id": trip_id, "status": "deduped", "trigger_stage": trigger_stage}

    user = get_user_by_id(user_id)
    recipients = _build_recipients(user, status.get("emergency_phone"))

    if trigger_stage == STAGE_1:
        alert_context = _resolve_trip_alert_context(trip_id, trip=trip, user=user)
        message = _build_stage_1_message(alert_context, force_stage_1_test_mode)
    else:
        alert_context = _resolve_trip_alert_context(trip_id, trip=trip, user=user)
        message = (
            "URGENT: SafePassage has not regained contact with "
            f"{alert_context.get('traveler_name') or 'the traveler'} for {offline_duration_minutes} minutes. "
            f"Itinerary: {_format_trip_window(alert_context)}. "
            f"Expected reconnect window: {adjusted_expected} minutes."
        )
    escalation_context = {
        "threshold_rule": "forced-stage-1-test-mode" if force_stage_1_test_mode else "offline > expected * multiplier",
        "location_risk": status.get("location_risk", "moderate"),
        "connectivity_risk": connectivity_risk,
        "battery_percent": battery_percent,
        "last_seen_lat": status.get("last_seen_lat"),
        "last_seen_lng": status.get("last_seen_lng"),
        "test_mode": force_stage_1_test_mode,
    }
    created_alert_event = _send_and_record_stage_alert(
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
        "alert_event": created_alert_event,
    }


def run_watchdog_cycle(now_utc: datetime | None = None) -> dict:
    """Run one full watchdog pass across active heartbeat-monitored trips."""
    now = now_utc or datetime.now(timezone.utc)
    today = now.date().isoformat()

    logger.info("[watchdog] cycle_started evaluated_at=%s", now.isoformat())

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
            results.append(_bootstrap_missing_status_with_stage_1(trip, now))
            continue
        results.append(evaluate_status_for_alert(status, now))

    alerts_created = [
        item.get("alert_event")
        for item in results
        if item.get("status") == "alerted" and isinstance(item.get("alert_event"), dict)
    ]

    logger.info(
        "[watchdog] cycle_finished evaluated_at=%s active_trip_count=%s result_count=%s alerts_created=%s",
        now.isoformat(),
        len(active_trips),
        len(results),
        len(alerts_created),
    )
    for alert in alerts_created:
        logger.info(
            "[watchdog] cycle_alert_detail alert_id=%s stage=%s user_id=%s trip_id=%s channels=%s",
            alert.get("id"),
            alert.get("stage"),
            alert.get("user_id"),
            alert.get("trip_id"),
            alert.get("channels"),
        )

    return {
        "evaluated_at": now.isoformat(),
        "active_trip_count": len(active_trips),
        "result_count": len(results),
        "alerts_created_count": len(alerts_created),
        "results": results,
    }
