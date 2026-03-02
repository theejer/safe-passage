"""Notification service tests for Telegram bot activation handling."""

from flask import Flask

from app.services import notifications


def test_start_command_with_phone_activates_contact(monkeypatch):
    app = Flask("test")

    captured_activation: dict = {}
    sent_messages: list[tuple[str, str, str]] = []

    def _fake_activate(phone: str, chat_id: str) -> dict:
        captured_activation["phone"] = phone
        captured_activation["chat_id"] = chat_id
        return {
            "id": "ec_1",
            "name": "Ravi",
            "phone": "+919100000001",
            "telegram_chat_id": chat_id,
            "telegram_bot_active": True,
        }

    monkeypatch.setattr(notifications, "activate_telegram_contact_by_phone", _fake_activate)
    monkeypatch.setattr(
        notifications,
        "_safe_send_message",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )

    notifications._handle_update(
        app,
        "bot-token",
        {
            "update_id": 1,
            "message": {
                "chat": {"id": 123456},
                "text": "/start +91 91000 00001",
            },
        },
    )

    assert captured_activation["chat_id"] == "123456"
    assert captured_activation["phone"] == "+919100000001"
    assert len(sent_messages) == 1
    assert "Activation successful" in sent_messages[0][2]


def test_start_command_without_phone_prompts_for_number(monkeypatch):
    app = Flask("test")

    sent_messages: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        notifications,
        "_safe_send_message",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )

    notifications._handle_update(
        app,
        "bot-token",
        {
            "update_id": 2,
            "message": {
                "chat": {"id": 999},
                "text": "/start",
            },
        },
    )

    assert len(sent_messages) == 1
    assert "Please send your phone number" in sent_messages[0][2]


def test_parse_stage_1_reply_yes_no_with_trip_id():
    assert notifications._parse_stage_1_reply("YES 44444444-4444-4444-4444-444444444444") == (
        True,
        "44444444-4444-4444-4444-444444444444",
    )
    assert notifications._parse_stage_1_reply("no 44444444-4444-4444-4444-444444444444") == (
        False,
        "44444444-4444-4444-4444-444444444444",
    )
    assert notifications._parse_stage_1_reply("YES") == (True, None)


def test_plain_yes_reply_resolves_single_open_stage1_trip(monkeypatch):
    app = Flask("test")

    sent_messages: list[tuple[str, str, str]] = []
    captured_args: dict = {}

    monkeypatch.setattr(
        notifications,
        "get_emergency_contact_context_by_chat_id",
        lambda _chat_id: {
            "user_id": "11111111-1111-1111-1111-111111111111",
            "contact_name": "JR",
        },
    )
    monkeypatch.setattr(
        notifications,
        "list_open_stage_1_trip_ids_for_user",
        lambda _user_id: ["44444444-4444-4444-4444-444444444444"],
    )
    monkeypatch.setattr(
        notifications,
        "_safe_send_message",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )

    from app.services import heartbeat_monitor

    def _fake_apply_stage_1_contact_response(**kwargs):
        captured_args.update(kwargs)
        return {"status": "deescalated", "stage": heartbeat_monitor.STAGE_3}

    monkeypatch.setattr(heartbeat_monitor, "apply_stage_1_contact_response", _fake_apply_stage_1_contact_response)

    notifications._handle_update(
        app,
        "bot-token",
        {
            "update_id": 4,
            "message": {
                "chat": {"id": 1037157942},
                "text": "YES",
            },
        },
    )

    assert captured_args["trip_id"] == "44444444-4444-4444-4444-444444444444"
    assert captured_args["can_contact"] is True
    assert len(sent_messages) == 1
    assert "recorded" in sent_messages[0][2].lower()


def test_yes_no_reply_applies_stage1_contact_response(monkeypatch):
    app = Flask("test")

    sent_messages: list[tuple[str, str, str]] = []
    captured_args: dict = {}

    monkeypatch.setattr(
        notifications,
        "get_emergency_contact_context_by_chat_id",
        lambda _chat_id: {
            "user_id": "11111111-1111-1111-1111-111111111111",
            "contact_name": "JR",
        },
    )
    monkeypatch.setattr(
        notifications,
        "_safe_send_message",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )

    from app.services import heartbeat_monitor

    def _fake_apply_stage_1_contact_response(**kwargs):
        captured_args.update(kwargs)
        return {"status": "deescalated", "stage": heartbeat_monitor.STAGE_3}

    monkeypatch.setattr(heartbeat_monitor, "apply_stage_1_contact_response", _fake_apply_stage_1_contact_response)

    notifications._handle_update(
        app,
        "bot-token",
        {
            "update_id": 3,
            "message": {
                "chat": {"id": 1037157942},
                "text": "NO 44444444-4444-4444-4444-444444444444",
            },
        },
    )

    assert captured_args["user_id"] == "11111111-1111-1111-1111-111111111111"
    assert captured_args["trip_id"] == "44444444-4444-4444-4444-444444444444"
    assert captured_args["can_contact"] is False
    assert captured_args["confirmed_by"] == "JR"
    assert len(sent_messages) == 1
    assert "response has been recorded" in sent_messages[0][2].lower()
