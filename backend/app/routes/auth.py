"""Optional auth/API-key routes.

Keeps authentication concerns separate from business logic routes.
"""

from flask import Blueprint, jsonify, request

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/validate-key")
def validate_api_key():
    """Minimal placeholder API key validation endpoint.

    In production, this would verify request keys against a secure store
    before allowing access to protected routes.
    """
    api_key = request.headers.get("x-api-key")
    is_valid = bool(api_key)
    return jsonify({"valid": is_valid})
