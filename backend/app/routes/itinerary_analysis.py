"""Itinerary analysis routes.

Connects parser and risk engine services, then persists risk reports.
"""

from uuid import uuid4

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.models.risk_reports import save_risk_report
from app.schemas.itinerary_schema import ItinerarySchema
from app.services.itinerary_parser import normalize_itinerary
from app.services.openai_risk_analyzer import OpenAIRiskAnalyzerError, analyze_itinerary_with_openai
from app.services.risk_engine import analyze_itinerary_risk
from app.utils.logging import get_logger

itinerary_analysis_bp = Blueprint("itinerary_analysis", __name__)
logger = get_logger(__name__)


def _sanitize_itinerary_payload(raw_itinerary: dict) -> dict:
    if not isinstance(raw_itinerary, dict):
        return {"days": [], "meta": {}}

    raw_days = raw_itinerary.get("days")
    if not isinstance(raw_days, list):
        raw_days = []

    sanitized_days: list[dict] = []
    for raw_day in raw_days:
        if not isinstance(raw_day, dict):
            continue

        raw_locations = raw_day.get("locations") if isinstance(raw_day.get("locations"), list) else []
        cleaned_locations: list[dict] = []

        for raw_location in raw_locations:
            if isinstance(raw_location, str):
                candidate_name = raw_location.strip()
                if candidate_name:
                    cleaned_locations.append({"name": candidate_name})
                continue

            if not isinstance(raw_location, dict):
                continue

            candidate_name = str(raw_location.get("name") or "").strip()
            if not candidate_name:
                continue

            cleaned_locations.append(
                {
                    "name": candidate_name,
                    "district": raw_location.get("district"),
                    "block": raw_location.get("block"),
                    "connectivity_zone": raw_location.get("connectivity_zone"),
                    "assumed_location_risk": raw_location.get("assumed_location_risk"),
                }
            )

        sanitized_days.append(
            {
                "date": raw_day.get("date"),
                "locations": cleaned_locations,
                "accommodation": raw_day.get("accommodation"),
            }
        )

    return {
        "days": sanitized_days,
        "meta": raw_itinerary.get("meta") if isinstance(raw_itinerary.get("meta"), dict) else {},
    }


@itinerary_analysis_bp.post("/analyze")
def analyze_route():
    """Parse incoming itinerary and compute Bihar-specific risk outputs."""
    body = request.get_json(force=True) or {}
    contract_version = body.get("contract_version", "1.0.0")
    request_id = body.get("request_id") or f"req_{uuid4().hex[:12]}"
    trip_id = body.get("trip_id")

    try:
        sanitized_itinerary = _sanitize_itinerary_payload(body.get("itinerary", {}))
        itinerary = ItinerarySchema.model_validate(sanitized_itinerary).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid itinerary payload", "details": exc.errors()}), 400

    normalized = normalize_itinerary(itinerary)
    logger.info("[RiskAnalyze] Start request_id=%s trip_id=%s days=%s", request_id, trip_id, len(normalized.get("days", [])))

    analyzer_mode = "openai"

    try:
        openai_result = analyze_itinerary_with_openai(normalized, request_id=request_id)
        report = openai_result.get("report", {})
        logger.info("[RiskAnalyze] OpenAI analyzer completed request_id=%s", request_id)
    except OpenAIRiskAnalyzerError as exc:
        logger.warning("OpenAI analyzer unavailable, using heuristic risk engine fallback: %s", exc)
        analyzer_mode = "heuristic_fallback"
        report = analyze_itinerary_risk(normalized)
        report.setdefault("recommendations", [])
        report.setdefault(
            "score",
            {
                "value": 60,
                "justification": "Fallback heuristic scoring used because OpenAI analyzer was unavailable.",
            },
        )

    saved = {}
    if trip_id:
        try:
            saved = save_risk_report(trip_id, report)
        except Exception as exc:
            logger.warning("Could not persist risk report for trip %s: %s", trip_id, exc)

    logger.info("[RiskAnalyze] Completed request_id=%s analyzer=%s saved=%s", request_id, analyzer_mode, bool(saved))

    return jsonify(
        {
            "contract_version": contract_version,
            "request_id": request_id,
            "analyzer": analyzer_mode,
            "report": report,
            "saved": saved,
        }
    )
