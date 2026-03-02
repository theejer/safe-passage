"""Incident sync routes for MITIGATION offline replay."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.incidents import record_incident_sync_job, upsert_incident

incidents_bp = Blueprint("incidents", __name__)


@incidents_bp.post("/sync")
def sync_incidents_route():
    payload = request.get_json(force=True) or {}
    incidents = payload.get("incidents") if isinstance(payload.get("incidents"), list) else []
    idempotency_key = str(payload.get("idempotency_key") or "").strip()

    if not incidents:
        return jsonify({"error": "incidents list is required"}), 400

    first = incidents[0] if isinstance(incidents[0], dict) else {}
    user_id = str(first.get("user_id") or "").strip()
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    normalized_incidents = []
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        created = upsert_incident(
            {
                "id": incident.get("incident_id") or incident.get("id"),
                "user_id": incident.get("user_id"),
                "trip_id": incident.get("trip_id"),
                "scenario_key": incident.get("scenario_key"),
                "occurred_at": incident.get("occurred_at"),
                "gps_lat": incident.get("gps_lat"),
                "gps_lng": incident.get("gps_lng"),
                "notes": incident.get("notes"),
                "severity": incident.get("severity"),
                "sync_status": "synced",
            }
        )
        if created:
            normalized_incidents.append(created)

    if idempotency_key:
        record_incident_sync_job(user_id=user_id, idempotency_key=idempotency_key, payload=payload, status="accepted")

    return jsonify({"sync_status": "synced", "synced_count": len(normalized_incidents)}), 200
