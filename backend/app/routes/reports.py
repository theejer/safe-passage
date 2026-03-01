"""Risk report routes backed by Supabase model helpers."""

from flask import Blueprint, jsonify, request

from app.models.risk_reports import latest_risk_report, save_risk_report

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

@reports_bp.post("")
def create_report():
    data = request.get_json() or {}
    trip_id = data.get("trip_id")
    report = data.get("report")
    summary = data.get("summary")

    if not trip_id or report is None:
        return jsonify({"error": "trip_id and report are required"}), 400

    payload = report if summary is None else {**report, "summary": summary}
    created = save_risk_report(trip_id, payload)

    return jsonify({
        "id": created.get("id"),
        "trip_id": created.get("trip_id"),
        "report": created.get("report"),
        "summary": summary,
        "created_at": created.get("created_at"),
    }), 201

@reports_bp.get("")
def list_reports():
    trip_id = request.args.get("trip_id")
    if not trip_id:
        return jsonify({"error": "trip_id query parameter is required"}), 400

    report = latest_risk_report(trip_id)
    if not report:
        return jsonify({"items": []}), 200

    return jsonify({"items": [report]}), 200