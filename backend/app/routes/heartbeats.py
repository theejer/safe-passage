"""Heartbeat ingestion routes.

Mobile clients send periodic status payloads for CURE monitoring.
"""

from flask import Blueprint, jsonify, request

from app.models.heartbeats import insert_heartbeat

heartbeats_bp = Blueprint("heartbeats", __name__)


@heartbeats_bp.post("")
def heartbeat_ingest_route():
    """Persist heartbeat ping used by offline anomaly monitor task."""
    payload = request.get_json(force=True)
    record = insert_heartbeat(payload)
    return jsonify(record), 201
