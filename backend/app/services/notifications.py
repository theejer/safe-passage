"""Notification service placeholders.

CURE monitoring task calls these functions to send alerts/escalations.
"""

from __future__ import annotations

import re
import threading
import time

import requests
from flask import Flask

from app.models.traveler_status import list_open_stage_1_trip_ids_for_user
from app.models.users import activate_telegram_contact_by_phone, get_emergency_contact_context_by_chat_id

_poller_thread: threading.Thread | None = None
_poller_stop_event: threading.Event | None = None


def _telegram_api_request(bot_token: str, method: str, payload: dict, timeout: int = 30) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _extract_phone_from_message(message: dict) -> str:
    contact = message.get("contact") or {}
    contact_phone = (contact.get("phone_number") or "").strip()
    if contact_phone:
        return contact_phone

    text = (message.get("text") or "").strip()
    if not text or text.startswith("/"):
        return ""

    cleaned = re.sub(r"[^0-9+]", "", text)
    return cleaned


def _extract_phone_from_start_command(text: str) -> str:
    command_text = (text or "").strip()
    if not command_text.startswith("/start"):
        return ""

    remainder = command_text[len("/start") :].strip()
    if not remainder:
        return ""

    return re.sub(r"[^0-9+]", "", remainder)


def _parse_stage_1_reply(text: str) -> tuple[bool, str | None] | None:
    """Parse `YES`/`NO` optionally followed by a trip id."""
    message_text = (text or "").strip()
    if not message_text:
        return None

    match = re.match(r"^(YES|NO)(?:\s+([0-9a-fA-F-]{36}))?$", message_text, flags=re.IGNORECASE)
    if not match:
        return None

    can_contact = match.group(1).upper() == "YES"
    trip_id = match.group(2)
    return can_contact, trip_id


def _safe_send_message(bot_token: str, chat_id: str, text: str) -> None:
    try:
        _telegram_api_request(
            bot_token,
            "sendMessage",
            {"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception:
        return


def _handle_update(app: Flask, bot_token: str, update: dict) -> None:
    message = update.get("message") or {}
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "").strip()
    if not chat_id:
        return

    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        phone_in_start = _extract_phone_from_start_command(text)
        if phone_in_start:
            activated = activate_telegram_contact_by_phone(phone_in_start, chat_id)
            if activated:
                _safe_send_message(
                    bot_token,
                    chat_id,
                    f"Activation successful for {activated.get('name')}. Telegram emergency alerts are now enabled.",
                )
            else:
                _safe_send_message(
                    bot_token,
                    chat_id,
                    "No matching emergency contact found for this phone number. Please ask the traveler to verify their emergency contact in the app.",
                )
            return

        _safe_send_message(
            bot_token,
            chat_id,
            "SafePassage bot connected. Please send your phone number to activate emergency alerts.",
        )
        return

    stage_1_reply = _parse_stage_1_reply(text)
    if stage_1_reply:
        can_contact, trip_id = stage_1_reply
        contact_context = get_emergency_contact_context_by_chat_id(chat_id)
        if not contact_context:
            _safe_send_message(
                bot_token,
                chat_id,
                "This chat is not linked to an active emergency contact. Please activate with /start <your_phone_number>.",
            )
            return

        user_id = str(contact_context.get("user_id") or "")
        contact_name = str(contact_context.get("contact_name") or "Emergency Contact")

        if not trip_id:
            open_stage_1_trip_ids = list_open_stage_1_trip_ids_for_user(user_id)
            if len(open_stage_1_trip_ids) == 1:
                trip_id = open_stage_1_trip_ids[0]
            elif len(open_stage_1_trip_ids) > 1:
                _safe_send_message(
                    bot_token,
                    chat_id,
                    "Multiple active Stage 1 alerts found. Please reply as YES <trip_id> or NO <trip_id>.",
                )
                return
            else:
                _safe_send_message(
                    bot_token,
                    chat_id,
                    "No active Stage 1 alert found right now.",
                )
                return

        try:
            with app.app_context():
                from app.services.heartbeat_monitor import apply_stage_1_contact_response

                result = apply_stage_1_contact_response(
                    user_id=user_id,
                    trip_id=trip_id,
                    can_contact=can_contact,
                    confirmed_by=contact_name,
                    source="telegram",
                )
        except Exception as exc:
            app.logger.warning(f"Failed processing stage-1 Telegram response: {exc}")
            _safe_send_message(bot_token, chat_id, "Sorry, we could not process your response. Please try again.")
            return

        status = str(result.get("status") or "")
        if status in {"deescalated", "escalated", "confirmed", "deduped"}:
            _safe_send_message(
                bot_token,
                chat_id,
                "Thanks. Your response has been recorded.",
            )
        elif status == "ignored-stage-mismatch":
            _safe_send_message(
                bot_token,
                chat_id,
                "This trip is no longer in Stage 1, so no action was applied.",
            )
        else:
            _safe_send_message(
                bot_token,
                chat_id,
                "Could not apply response for this trip right now.",
            )
        return

    phone = _extract_phone_from_message(message)
    if not phone:
        return

    activated = activate_telegram_contact_by_phone(phone, chat_id)
    if activated:
        _safe_send_message(
            bot_token,
            chat_id,
            f"Activation successful for {activated.get('name')}. Telegram emergency alerts are now enabled.",
        )
    else:
        _safe_send_message(
            bot_token,
            chat_id,
            "No matching emergency contact found for this phone number. Please ask the traveler to verify your contact phone in the app.",
        )


def _run_poller(app: Flask, bot_token: str, poll_interval_seconds: int, stop_event: threading.Event) -> None:
    offset = 0
    while not stop_event.is_set():
        try:
            updates_response = _telegram_api_request(
                bot_token,
                "getUpdates",
                {"timeout": 20, "offset": offset},
                timeout=30,
            )
            if not updates_response.get("ok"):
                stop_event.wait(poll_interval_seconds)
                continue

            for update in updates_response.get("result", []):
                update_id = int(update.get("update_id", 0))
                if update_id:
                    offset = max(offset, update_id + 1)
                _handle_update(app, bot_token, update)

        except Exception as exc:
            app.logger.warning(f"Telegram poller error: {exc}")
            time.sleep(poll_interval_seconds)


def start_telegram_bot_poller(app: Flask) -> bool:
    """Start Telegram long-polling loop in a background daemon thread."""
    global _poller_thread, _poller_stop_event

    if _poller_thread and _poller_thread.is_alive():
        return True

    if not app.config.get("TELEGRAM_BOT_ENABLED", False):
        app.logger.info("Telegram bot poller is disabled by config.")
        return False

    token = app.config.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        app.logger.warning("Telegram bot is enabled but TELEGRAM_BOT_TOKEN is missing.")
        return False

    poll_interval_seconds = max(1, int(app.config.get("TELEGRAM_POLL_INTERVAL_SECONDS", 2)))
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_poller,
        args=(app, token, poll_interval_seconds, stop_event),
        name="telegram-bot-poller",
        daemon=True,
    )
    thread.start()

    _poller_stop_event = stop_event
    _poller_thread = thread
    app.logger.info("Telegram bot poller started.")
    return True


def send_telegram_alert(chat_id: str, message: str, bot_token: str | None = None) -> dict:
    """Send one Telegram message to an activated emergency contact chat id."""
    token = (bot_token or "").strip()
    if not token:
        return {
            "channel": "telegram",
            "to": chat_id,
            "queued": False,
            "error": "missing-bot-token",
        }

    try:
        response = _telegram_api_request(
            token,
            "sendMessage",
            {"chat_id": chat_id, "text": message},
            timeout=15,
        )
        return {
            "channel": "telegram",
            "to": chat_id,
            "queued": bool(response.get("ok")),
            "provider_response": response,
        }
    except Exception as exc:
        return {
            "channel": "telegram",
            "to": chat_id,
            "queued": False,
            "error": str(exc),
        }


def send_sms_alert(phone_number: str, message: str) -> dict:
    """Legacy SMS placeholder retained for backward compatibility."""
    return {"channel": "sms", "to": phone_number, "queued": True, "message": message}


def send_push_alert(device_token: str, payload: dict) -> dict:
    """Placeholder for FCM push notifications to emergency contacts/users."""
    return {"channel": "push", "to": device_token, "queued": True, "payload": payload}


def send_email_alert(email: str, subject: str, html_body: str) -> dict:
    """Placeholder for escalation emails with incident context attachments."""
    return {"channel": "email", "to": email, "queued": True, "subject": subject}
