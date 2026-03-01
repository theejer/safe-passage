"""User routes for account and emergency contact updates.

This blueprint validates request payloads then calls model wrappers.
"""

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.models.users import create_user, get_user_by_id, update_emergency_contact
from app.schemas.user_schema import EmergencyContactSchema, UserCreateSchema

users_bp = Blueprint("users", __name__)


@users_bp.post("")
def create_user_route():
    """Create a user profile used by trips, alerts, and incident flows."""
    try:
        payload = UserCreateSchema.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid user payload", "details": exc.errors()}), 400

    created = create_user(payload)
    return jsonify(created), 201


@users_bp.get("/<user_id>")
def get_user_route(user_id: str):
    """Fetch a user profile by id."""
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


@users_bp.patch("/<user_id>/emergency-contact")
def update_contact_route(user_id: str):
    """Update emergency contact consumed by notification service."""
    try:
        payload = EmergencyContactSchema.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid emergency contact payload", "details": exc.errors()}), 400

    updated = update_emergency_contact(user_id, payload)
    return jsonify(updated)
