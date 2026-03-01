"""Heartbeat ingestion routes.

Mobile clients send periodic status payloads for CURE monitoring.
"""

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError

from app.models.heartbeats import insert_heartbeat
from app.models.trips import get_trip_by_id
from app.schemas.heartbeat_schema import HeartbeatIngestSchema
from app.services.heartbeat_monitor import run_watchdog_cycle, process_heartbeat_ingest
from app.utils.auth import extract_bearer_token, verify_supabase_user_id

heartbeats_bp = Blueprint("heartbeats", __name__)


@heartbeats_bp.post("")
def heartbeat_ingest_route():
    """Persist heartbeat ping used by offline anomaly monitor task."""
    try:
        token = extract_bearer_token(request)
        auth_user_id = verify_supabase_user_id(token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    try:
        payload = HeartbeatIngestSchema.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid heartbeat payload", "details": exc.errors()}), 400

    if payload["user_id"] != auth_user_id:
        return jsonify({"error": "user_id does not match token subject"}), 403

    trip = get_trip_by_id(payload["trip_id"])
    if not trip:
        return jsonify({"error": "trip not found"}), 404
    if trip.get("user_id") != auth_user_id:
        return jsonify({"error": "trip does not belong to token user"}), 403
    if trip.get("heartbeat_enabled") is False:
        return jsonify({"error": "heartbeat monitoring disabled for trip"}), 409

    gps = payload.get("gps") or {}
    heartbeat_row = {
        "user_id": payload["user_id"],
        "trip_id": payload["trip_id"],
        "timestamp": payload["timestamp"],
        "gps_lat": gps.get("lat"),
        "gps_lng": gps.get("lng"),
        "accuracy_meters": gps.get("accuracy_meters"),
        "battery_percent": payload.get("battery_percent"),
        "network_status": payload.get("network_status"),
        "offline_minutes": payload.get("offline_minutes"),
        "source": payload.get("source"),
        "emergency_phone": payload.get("emergency_phone"),
    }
    insert_heartbeat(heartbeat_row)
    process_heartbeat_ingest(heartbeat_row)

    return ("", 204)


@heartbeats_bp.post("/watchdog/run")
def heartbeat_watchdog_run_route():
    """Run one watchdog evaluation cycle (internal/scheduler endpoint)."""
    watchdog_key = current_app.config.get("HEARTBEAT_WATCHDOG_KEY", "")
    if watchdog_key:
        provided = request.headers.get("x-watchdog-key", "")
        if provided != watchdog_key:
            return jsonify({"error": "invalid watchdog key"}), 401

    result = run_watchdog_cycle()
    return jsonify(result)
