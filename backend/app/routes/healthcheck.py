"""Healthcheck endpoint blueprint.

Used by deployments and monitoring systems to verify API process health.
"""

from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import sqlalchemy_engine

healthcheck_bp = Blueprint("healthcheck", __name__)


@healthcheck_bp.get("/health")
def healthcheck():
    """Health endpoint that verifies both server and database connectivity."""
    health_status = {"status": "ok", "server": "up", "database": "unknown"}

    # Check database connectivity
    if sqlalchemy_engine is None:
        health_status["status"] = "degraded"
        health_status["database"] = "not_configured"
        return jsonify(health_status), 503

    try:
        with sqlalchemy_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.commit()
        health_status["database"] = "up"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = "down"
        health_status["error"] = str(e)
        return jsonify(health_status), 503

    return jsonify(health_status)
