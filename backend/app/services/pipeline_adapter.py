from __future__ import annotations

from typing import Any

from app.services.pipeline_backend import ANALYZER_MODEL, DEFAULT_MODEL, run_itinerary_pipeline


def _as_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_iso2(value: Any) -> str | None:
    text = _as_optional_text(value)
    if not text:
        return None
    upper = text.upper()
    if len(upper) == 2 and upper.isalpha():
        return upper
    return None


def _extract_parser_context(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    trip_name = _as_optional_text(payload.get("trip_name")) or _as_optional_text(metadata.get("trip_name"))
    start_date = _as_optional_text(payload.get("start_date")) or _as_optional_text(metadata.get("start_date"))
    end_date = _as_optional_text(payload.get("end_date")) or _as_optional_text(metadata.get("end_date"))
    destination_country = _normalize_iso2(payload.get("destination_country")) or _normalize_iso2(metadata.get("destination_country"))

    return {
        "trip_name": trip_name,
        "start_date": start_date,
        "end_date": end_date,
        "destination_country": destination_country,
    }


def analyze_trip(payload: dict[str, Any]) -> dict[str, Any]:
    itinerary = str(payload.get("itinerary") or "").strip()
    if not itinerary:
        return {
            "status": "failed",
            "stage": "input",
            "details": {"error": "itinerary is required"},
        }

    parser_model = str(payload.get("parser_model") or DEFAULT_MODEL)
    analyzer_model = str(payload.get("analyzer_model") or ANALYZER_MODEL)
    parser_context = _extract_parser_context(payload)

    return run_itinerary_pipeline(
        itinerary,
        model=parser_model,
        analyzer_model=analyzer_model,
        parser_context=parser_context,
    )
