"""User data-access wrappers over SQLAlchemy.

Routes and services call these helpers to keep database queries centralized.
"""

from uuid import UUID, uuid4

from sqlalchemy import text

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _normalize_phone(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    keep_plus = raw.startswith("+")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return ""

    return f"+{digits}" if keep_plus else digits


def _attach_primary_emergency_contact(user_row: dict) -> dict:
    query = text(
        """
        SELECT name, phone, telegram_chat_id, telegram_bot_active
        FROM emergency_contacts
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        contact_row = connection.execute(query, {"user_id": user_row["id"]}).mappings().first()

    if contact_row:
        user_row["emergency_contact"] = {
            "name": contact_row.get("name"),
            "phone": contact_row.get("phone"),
            "telegram_chat_id": contact_row.get("telegram_chat_id"),
            "telegram_bot_active": bool(contact_row.get("telegram_bot_active")),
        }

    return user_row


def create_user(payload: dict) -> dict:
    """Insert user record and return created row metadata."""
    candidate_id = str(payload.get("id") or "").strip()
    user_id = candidate_id if _is_uuid(candidate_id) else str(uuid4())

    insert_user_query = text(
        """
        INSERT INTO users (id, full_name, phone)
        VALUES (:id, :full_name, :phone)
        RETURNING *
        """
    )

    emergency_contact = payload.get("emergency_contact") or {}
    emergency_name = (emergency_contact.get("name") or "").strip()
    emergency_phone = _normalize_phone(emergency_contact.get("phone"))

    with get_db_engine().begin() as connection:
        user_row = connection.execute(
            insert_user_query,
            {
                "id": user_id,
                "full_name": payload.get("full_name"),
                "phone": payload.get("phone"),
            },
        ).mappings().first()

        if emergency_name and emergency_phone:
            insert_contact_query = text(
                """
                INSERT INTO emergency_contacts (id, user_id, name, phone, telegram_chat_id, telegram_bot_active)
                VALUES (:id, :user_id, :name, :phone, NULL, FALSE)
                """
            )
            connection.execute(
                insert_contact_query,
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": emergency_name,
                    "phone": emergency_phone,
                },
            )

    if not user_row:
        return {}

    return _attach_primary_emergency_contact(dict(user_row))


def get_user_by_id(user_id: str) -> dict:
    """Fetch a user record by id."""
    if not _is_uuid(user_id):
        return {}

    query = text("SELECT * FROM users WHERE id = :user_id LIMIT 1")
    with get_db_engine().begin() as connection:
        row = connection.execute(query, {"user_id": user_id}).mappings().first()

    if not row:
        return {}

    return _attach_primary_emergency_contact(dict(row))


def update_emergency_contact(user_id: str, contact_payload: dict) -> dict:
    """Update emergency contact details used by notification services."""
    if not _is_uuid(user_id):
        return {}

    name = (contact_payload.get("name") or "").strip()
    phone = _normalize_phone(contact_payload.get("phone"))
    if not name or not phone:
        return get_user_by_id(user_id)

    with get_db_engine().begin() as connection:
        existing_primary = connection.execute(
            text(
                """
                SELECT id
                FROM emergency_contacts
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).mappings().first()

        if existing_primary:
            connection.execute(
                text(
                    """
                    UPDATE emergency_contacts
                    SET name = :name,
                        phone = :phone,
                        telegram_chat_id = NULL,
                        telegram_bot_active = FALSE
                    WHERE id = :contact_id
                    """
                ),
                {
                    "contact_id": existing_primary["id"],
                    "name": name,
                    "phone": phone,
                },
            )
        else:
            connection.execute(
                text(
                    """
                    INSERT INTO emergency_contacts (id, user_id, name, phone, telegram_chat_id, telegram_bot_active)
                    VALUES (:id, :user_id, :name, :phone, NULL, FALSE)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": name,
                    "phone": phone,
                },
            )

    return get_user_by_id(user_id)


def activate_telegram_contact_by_phone(phone: str, chat_id: str) -> dict:
    """Activate Telegram notifications for the latest contact matching phone."""
    normalized_phone = _normalize_phone(phone)
    normalized_chat_id = (chat_id or "").strip()
    if not normalized_phone or not normalized_chat_id:
        return {}

    with get_db_engine().begin() as connection:
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
            (
                row
                for row in contacts
                if _normalize_phone(row.get("phone")) == normalized_phone
            ),
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
            {"contact_id": matched["id"], "chat_id": normalized_chat_id},
        )

    return {
        "id": matched.get("id"),
        "user_id": matched.get("user_id"),
        "name": matched.get("name"),
        "phone": matched.get("phone"),
        "telegram_chat_id": normalized_chat_id,
        "telegram_bot_active": True,
    }


def get_emergency_contact_context_by_chat_id(chat_id: str) -> dict:
    """Resolve emergency contact and traveler context for an activated Telegram chat id."""
    normalized_chat_id = (chat_id or "").strip()
    if not normalized_chat_id:
        return {}

    query = text(
        """
        SELECT
            ec.id AS contact_id,
            ec.user_id,
            ec.name AS contact_name,
            ec.phone AS contact_phone,
            ec.telegram_chat_id,
            ec.telegram_bot_active,
            u.full_name AS traveler_name
        FROM emergency_contacts ec
        JOIN users u ON u.id = ec.user_id
        WHERE ec.telegram_chat_id = :chat_id
          AND ec.telegram_bot_active = TRUE
        ORDER BY ec.created_at DESC
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(query, {"chat_id": normalized_chat_id}).mappings().first()

    return dict(row) if row else {}
