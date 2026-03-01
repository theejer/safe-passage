"""Scheduled monitoring task for CURE pillar.

This task is intended to run on a cron scheduler. It compares latest
heartbeats against expected offline windows and triggers alerts.
"""

from app.models.heartbeats import list_recent_heartbeats
from app.services.connectivity_model import should_trigger_alert
from app.services.notifications import send_sms_alert


def run_monitor_for_user(user_id: str, expected_offline_minutes: int) -> dict:
    """Example monitor flow for one user.

    Interactions:
    - reads heartbeat history from models.heartbeats
    - evaluates threshold via services.connectivity_model
    - dispatches notifications via services.notifications
    """
    heartbeats = list_recent_heartbeats(user_id, limit=1)
    if not heartbeats:
        return {"user_id": user_id, "status": "no-heartbeat"}

    latest = heartbeats[0]
    actual_offline_minutes = int(latest.get("offline_minutes", 0))

    if should_trigger_alert(actual_offline_minutes, expected_offline_minutes):
        send_sms_alert(
            latest.get("emergency_phone", ""),
            f"SafePassage Alert: offline {actual_offline_minutes} minutes.",
        )
        return {"user_id": user_id, "status": "alert-triggered"}

    return {"user_id": user_id, "status": "within-expected-window"}
