"""User routes for account and emergency contact updates.

This blueprint validates request payloads then calls model wrappers.
"""

from flask import Blueprint, jsonify, request

from app.models.users import create_user, update_emergency_contact
from app.schemas.user_schema import EmergencyContactSchema, UserCreateSchema

users_bp = Blueprint("users", __name__)


@users_bp.post("")
def create_user_route():
    """Create a user profile used by trips, alerts, and incident flows."""
    payload = UserCreateSchema.model_validate(request.get_json(force=True)).model_dump()
    created = create_user(payload)
    return jsonify(created), 201


@users_bp.patch("/<user_id>/emergency-contact")
def update_contact_route(user_id: str):
    """Update emergency contact consumed by notification service."""
    payload = EmergencyContactSchema.model_validate(request.get_json(force=True)).model_dump()
    updated = update_emergency_contact(user_id, payload)
    return jsonify(updated)
