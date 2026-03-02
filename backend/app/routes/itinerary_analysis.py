"""Itinerary analysis routes.

Connects parser and risk engine services, then persists risk reports.
"""

from uuid import uuid4

from flask import Blueprint, jsonify, request

from app.models.risk_reports import save_risk_report
from app.schemas.itinerary_schema import ItinerarySchema
from app.services.itinerary_parser import normalize_itinerary
from app.services.openai_risk_analyzer import OpenAIRiskAnalyzerError, analyze_itinerary_with_openai
from app.services.risk_engine import analyze_itinerary_risk
from app.utils.logging import get_logger

itinerary_analysis_bp = Blueprint("itinerary_analysis", __name__)
logger = get_logger(__name__)


@itinerary_analysis_bp.post("/analyze")
def analyze_route():
    """Parse incoming itinerary and compute Bihar-specific risk outputs."""
    body = request.get_json(force=True)
    contract_version = body.get("contract_version", "1.0.0")
    request_id = body.get("request_id") or f"req_{uuid4().hex[:12]}"
    trip_id = body.get("trip_id")
    itinerary = ItinerarySchema.model_validate(body.get("itinerary", {})).model_dump()

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
