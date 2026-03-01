"""Healthcheck endpoint blueprint.

Used by deployments and monitoring systems to verify API process health.
"""

from flask import Blueprint, jsonify

healthcheck_bp = Blueprint("healthcheck", __name__)


@healthcheck_bp.get("/health")
def healthcheck():
    """Simple liveness endpoint; does not verify external dependencies."""
    return jsonify({"status": "ok"})
