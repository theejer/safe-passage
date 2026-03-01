"""Itinerary analysis routes.

Connects parser and risk engine services, then persists risk reports.
"""

from flask import Blueprint, jsonify, request

from app.models.risk_reports import save_risk_report
from app.schemas.itinerary_schema import ItinerarySchema
from app.services.itinerary_parser import normalize_itinerary
from app.services.risk_engine import analyze_itinerary_risk

itinerary_analysis_bp = Blueprint("itinerary_analysis", __name__)


@itinerary_analysis_bp.post("/analyze")
def analyze_route():
    """Parse incoming itinerary and compute Bihar-specific risk outputs."""
    body = request.get_json(force=True)
    trip_id = body.get("trip_id")
    itinerary = ItinerarySchema.model_validate(body.get("itinerary", {})).model_dump()

    normalized = normalize_itinerary(itinerary)
    report = analyze_itinerary_risk(normalized)
    saved = save_risk_report(trip_id, report)

    return jsonify({"report": report, "saved": saved})
