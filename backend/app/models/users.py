"""User data-access wrappers over Supabase.

Routes and services call these helpers to keep database queries centralized.
"""

from app.extensions import get_supabase


def create_user(payload: dict) -> dict:
    """Insert user record and return created row metadata."""
    response = get_supabase().table("users").insert(payload).execute()
    return response.data[0] if response.data else {}


def update_emergency_contact(user_id: str, contact_payload: dict) -> dict:
    """Update emergency contact details used by notification services."""
    response = (
        get_supabase()
        .table("users")
        .update({"emergency_contact": contact_payload})
        .eq("id", user_id)
        .execute()
    )
    return response.data[0] if response.data else {}
