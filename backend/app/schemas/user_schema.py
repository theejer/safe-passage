"""Pydantic schemas for user-related request payloads.

Route handlers validate input with these models before writing to DB.
"""

from pydantic import BaseModel, Field


class EmergencyContactSchema(BaseModel):
    """Emergency contact details used by CURE alert routing."""

    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=8, max_length=20)
    telegram_chat_id: str | None = None
    telegram_bot_active: bool = False


class UserCreateSchema(BaseModel):
    """Minimal user profile shape for app onboarding."""

    id: str | None = None
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=8, max_length=20)
    emergency_contact: EmergencyContactSchema | None = None
