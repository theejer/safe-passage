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


def _attach_primary_emergency_contact(user_row: dict) -> dict:
    query = text(
        """
        SELECT name, phone, email
        FROM emergency_contacts
        WHERE user_id = :user_id
        ORDER BY is_primary DESC, created_at DESC
        LIMIT 1
        """
    )

    with get_db_engine().begin() as connection:
        contact_row = connection.execute(query, {"user_id": user_row["id"]}).mappings().first()

    if contact_row:
        user_row["emergency_contact"] = {
            "name": contact_row.get("name"),
            "phone": contact_row.get("phone"),
            "email": contact_row.get("email"),
        }

    return user_row


def create_user(payload: dict) -> dict:
    """Insert user record and return created row metadata."""
    user_id = str(uuid4())

    insert_user_query = text(
        """
        INSERT INTO users (id, full_name, phone)
        VALUES (:id, :full_name, :phone)
        RETURNING *
        """
    )

    emergency_contact = payload.get("emergency_contact") or {}
    emergency_name = (emergency_contact.get("name") or "").strip()
    emergency_phone = (emergency_contact.get("phone") or "").strip()
    emergency_email = emergency_contact.get("email")

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
                INSERT INTO emergency_contacts (id, user_id, name, phone, email, is_primary)
                VALUES (:id, :user_id, :name, :phone, :email, TRUE)
                """
            )
            connection.execute(
                insert_contact_query,
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": emergency_name,
                    "phone": emergency_phone,
                    "email": emergency_email,
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
    phone = (contact_payload.get("phone") or "").strip()
    email = contact_payload.get("email")
    if not name or not phone:
        return get_user_by_id(user_id)

    with get_db_engine().begin() as connection:
        existing_primary = connection.execute(
            text(
                """
                SELECT id
                FROM emergency_contacts
                WHERE user_id = :user_id
                ORDER BY is_primary DESC, created_at DESC
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
                        email = :email,
                        is_primary = TRUE
                    WHERE id = :contact_id
                    """
                ),
                {
                    "contact_id": existing_primary["id"],
                    "name": name,
                    "phone": phone,
                    "email": email,
                },
            )
        else:
            connection.execute(
                text(
                    """
                    INSERT INTO emergency_contacts (id, user_id, name, phone, email, is_primary)
                    VALUES (:id, :user_id, :name, :phone, :email, TRUE)
                    """
                ),
                {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "name": name,
                    "phone": phone,
                    "email": email,
                },
            )

    return get_user_by_id(user_id)
