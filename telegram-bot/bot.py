from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("telegram-bot")


def normalize_phone(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    keep_plus = raw.startswith("+")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""

    return f"+{digits}" if keep_plus else digits


def extract_phone_from_start_command(text: str) -> str:
    command_text = (text or "").strip()
    if not command_text.startswith("/start"):
        return ""

    remainder = command_text[len("/start") :].strip()
    if not remainder:
        return ""

    return normalize_phone(re.sub(r"[^0-9+]", "", remainder))


def extract_phone_from_message(message: dict) -> str:
    contact = message.get("contact") or {}
    contact_phone = normalize_phone(contact.get("phone_number"))
    if contact_phone:
        return contact_phone

    text = (message.get("text") or "").strip()
    if not text or text.startswith("/"):
        return ""

    cleaned = re.sub(r"[^0-9+]", "", text)
    return normalize_phone(cleaned)


@dataclass
class BotConfig:
    telegram_bot_token: str
    sqlalchemy_database_uri: str
    backend_base_url: str
    heartbeat_watchdog_key: str
    poll_interval_seconds: int = 2


class EmergencyContactRepository:
    def __init__(self, sqlalchemy_database_uri: str) -> None:
        self.engine = create_engine(sqlalchemy_database_uri, pool_pre_ping=True)

    def activate_by_phone(self, phone: str, chat_id: str) -> dict:
        normalized_phone = normalize_phone(phone)
        if not normalized_phone:
            return {}

        with self.engine.begin() as connection:
            contacts = connection.execute(
                text(
                    """
                    SELECT id, user_id, name, phone
                    FROM emergency_contacts
                    ORDER BY created_at DESC
                    """
                )
            ).mappings().all()

            matched = next(
                (row for row in contacts if normalize_phone(row.get("phone")) == normalized_phone),
                None,
            )
            if not matched:
                return {}

            connection.execute(
                text(
                    """
                    UPDATE emergency_contacts
                    SET telegram_chat_id = :chat_id,
                        telegram_bot_active = TRUE
                    WHERE id = :contact_id
                    """
                ),
                {"chat_id": str(chat_id), "contact_id": matched["id"]},
            )

        return {
            "id": matched.get("id"),
            "user_id": matched.get("user_id"),
            "name": matched.get("name"),
            "phone": matched.get("phone"),
            "telegram_chat_id": str(chat_id),
            "telegram_bot_active": True,
        }

    def get_contact_context_by_chat_id(self, chat_id: str) -> dict:
        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT ec.user_id, ec.name AS contact_name
                    FROM emergency_contacts ec
                    WHERE ec.telegram_chat_id = :chat_id
                      AND ec.telegram_bot_active = TRUE
                    ORDER BY ec.created_at DESC
                    LIMIT 1
                    """
                ),
                {"chat_id": str(chat_id)},
            ).mappings().first()

        return dict(row) if row else {}

    def list_open_stage_1_trip_ids_for_user(self, user_id: str) -> list[str]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT trip_id
                    FROM traveler_status
                    WHERE user_id = :user_id
                      AND current_stage = 'stage_1_initial_alert'
                      AND monitoring_state <> 'resolved'
                    ORDER BY last_stage_change_at DESC NULLS LAST, updated_at DESC
                    """
                ),
                {"user_id": user_id},
            ).mappings().all()

        return [str(row.get("trip_id")) for row in rows if row.get("trip_id")]


class TelegramBotService:
    def __init__(self, config: BotConfig, repository: EmergencyContactRepository) -> None:
        self.config = config
        self.repository = repository
        self.offset = 0

    def _api_request(self, method: str, payload: dict, timeout: int = 30) -> dict:
        response = requests.post(
            f"https://api.telegram.org/bot{self.config.telegram_bot_token}/{method}",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def _send_message(self, chat_id: str, message: str, reply_markup: dict | None = None) -> None:
        try:
            payload: dict = {"chat_id": chat_id, "text": message}
            if reply_markup is not None:
                payload["reply_markup"] = reply_markup
            self._api_request("sendMessage", payload, timeout=15)
        except Exception as exc:
            logger.warning("Telegram sendMessage failed: %s", exc)

    def _yes_no_keyboard(self) -> dict:
        return {
            "keyboard": [[{"text": "YES"}, {"text": "NO"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False,
            "input_field_placeholder": "Use buttons to respond",
        }

    def _send_response_buttons(self, chat_id: str) -> None:
        self._send_message(
            chat_id,
            "Use these buttons for response accuracy when you receive an emergency check:",
            reply_markup=self._yes_no_keyboard(),
        )

    def _attempt_activation(self, chat_id: str, phone: str) -> None:
        activated = self.repository.activate_by_phone(phone, chat_id)
        if activated:
            self._send_message(
                chat_id,
                f"Activation successful for {activated.get('name')}. Telegram emergency alerts are now enabled.",
            )
            self._send_response_buttons(chat_id)
            return

        self._send_message(
            chat_id,
            "No matching emergency contact found for this phone number. Please ask the traveler to verify your number in SafePassage.",
        )

    def _submit_stage_1_response(
        self,
        *,
        user_id: str,
        trip_id: str,
        response_text: str,
        confirmed_by: str,
    ) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.config.heartbeat_watchdog_key:
            headers["x-watchdog-key"] = self.config.heartbeat_watchdog_key

        response = requests.post(
            f"{self.config.backend_base_url.rstrip('/')}/heartbeats/watchdog/respond",
            json={
                "user_id": user_id,
                "trip_id": trip_id,
                "response": response_text,
                "confirmed_by": confirmed_by,
                "source": "telegram",
            },
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _parse_stage_response(self, text_value: str) -> tuple[str, str | None] | None:
        match = re.match(r"^(YES|NO)(?:\s+([0-9a-fA-F-]{36}))?$", (text_value or "").strip(), flags=re.IGNORECASE)
        if not match:
            return None
        return match.group(1).upper(), match.group(2)

    def _handle_stage_response(self, chat_id: str, text_value: str) -> bool:
        parsed = self._parse_stage_response(text_value)
        if not parsed:
            return False

        response_text, explicit_trip_id = parsed
        contact_context = self.repository.get_contact_context_by_chat_id(chat_id)
        if not contact_context:
            self._send_message(
                chat_id,
                "This chat is not linked to an active emergency contact. Activate with /start <your_phone>.",
            )
            return True

        user_id = str(contact_context.get("user_id") or "")
        contact_name = str(contact_context.get("contact_name") or "Emergency Contact")
        if not user_id:
            self._send_message(chat_id, "Could not resolve linked user for this chat.")
            return True

        trip_id = explicit_trip_id
        if not trip_id:
            open_trip_ids = self.repository.list_open_stage_1_trip_ids_for_user(user_id)
            if len(open_trip_ids) == 1:
                trip_id = open_trip_ids[0]
            elif len(open_trip_ids) > 1:
                self._send_message(
                    chat_id,
                    "Multiple active Stage 1 alerts found. Please reply as YES <trip_id> or NO <trip_id>.",
                )
                return True
            else:
                self._send_message(chat_id, "No active Stage 1 alert found right now.")
                return True

        try:
            result = self._submit_stage_1_response(
                user_id=user_id,
                trip_id=trip_id,
                response_text=response_text,
                confirmed_by=contact_name,
            )
        except Exception as exc:
            logger.warning("Failed to submit stage response: %s", exc)
            self._send_message(chat_id, "Sorry, we could not process your response right now. Please try again.")
            return True

        status = str(result.get("status") or "")
        if status in {"deescalated", "escalated", "confirmed", "deduped"}:
            self._send_message(chat_id, "Thanks. Your response has been recorded.")
        elif status == "ignored-stage-mismatch":
            self._send_message(chat_id, "This trip is no longer in Stage 1, so no action was applied.")
        else:
            self._send_message(chat_id, "Could not apply response for this trip right now.")

        return True

    def _process_update(self, update: dict) -> None:
        message = update.get("message") or {}
        if not message:
            return

        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "").strip()
        if not chat_id:
            return

        text_value = (message.get("text") or "").strip()
        if text_value.startswith("/start"):
            start_phone = extract_phone_from_start_command(text_value)
            if start_phone:
                self._attempt_activation(chat_id, start_phone)
                return

            self._send_message(
                chat_id,
                "SafePassage bot connected. Send /start <your_phone> or send your phone number in a separate message to activate alerts.",
            )
            return

        if text_value.lower().startswith("/respond"):
            self._send_response_buttons(chat_id)
            return

        if self._handle_stage_response(chat_id, text_value):
            return

        phone = extract_phone_from_message(message)
        if phone:
            self._attempt_activation(chat_id, phone)

    def run_forever(self) -> None:
        logger.info("Telegram bot poller started.")
        while True:
            try:
                updates_response = self._api_request(
                    "getUpdates",
                    {"timeout": 20, "offset": self.offset},
                    timeout=30,
                )
                if not updates_response.get("ok"):
                    time.sleep(self.config.poll_interval_seconds)
                    continue

                for update in updates_response.get("result", []):
                    update_id = int(update.get("update_id", 0))
                    if update_id:
                        self.offset = max(self.offset, update_id + 1)
                    self._process_update(update)

            except Exception as exc:
                logger.warning("Telegram poller error: %s", exc)
                time.sleep(self.config.poll_interval_seconds)


def load_config() -> BotConfig:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    db_uri = os.getenv("SQLALCHEMY_DATABASE_URI", "").strip()
    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:5000").strip()
    watchdog_key = os.getenv("HEARTBEAT_WATCHDOG_KEY", "").strip()
    poll_interval = int(os.getenv("TELEGRAM_POLL_INTERVAL_SECONDS", "2"))

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
    if not db_uri:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is required.")

    return BotConfig(
        telegram_bot_token=token,
        sqlalchemy_database_uri=db_uri,
        backend_base_url=backend_base_url,
        heartbeat_watchdog_key=watchdog_key,
        poll_interval_seconds=max(1, poll_interval),
    )


def main() -> None:
    config = load_config()
    repository = EmergencyContactRepository(config.sqlalchemy_database_uri)
    TelegramBotService(config, repository).run_forever()


if __name__ == "__main__":
    main()
