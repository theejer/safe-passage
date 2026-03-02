"""Trip and itinerary management routes.

These handlers orchestrate schema validation, model persistence,
and service operations for PREVENTION data setup.
"""

import os
import tempfile
from typing import Any
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.models.itineraries import get_itinerary, upsert_itinerary
from app.models.trips import create_trip, list_trips_by_user
from app.schemas.itinerary_schema import ItinerarySchema
from app.schemas.trip_schema import TripCreateSchema
from app.services.pdf_parser import extract_itinerary_from_document, extract_itinerary_from_text
from app.utils.logging import get_logger

logger = get_logger(__name__)
trips_bp = Blueprint("trips", __name__)


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_itinerary_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize parser/generator output into ItinerarySchema-compatible shape."""
    root = raw if isinstance(raw, dict) else {}
    raw_days = root.get("days")
    if not isinstance(raw_days, list):
        raw_days = root.get("DAY") if isinstance(root.get("DAY"), list) else []

    normalized_days: list[dict[str, Any]] = []
    for index, raw_day in enumerate(raw_days):
        if not isinstance(raw_day, dict):
            continue

        date_value = (
            _as_text(raw_day.get("date"))
            or _as_text(raw_day.get("day_date"))
            or _as_text(raw_day.get("day_label"))
            or f"Day {index + 1}"
        )

        raw_locations = raw_day.get("locations")
        if not isinstance(raw_locations, list):
            activity_entries = raw_day.get("ACTIVITY") if isinstance(raw_day.get("ACTIVITY"), list) else []
            raw_locations = []
            for activity in activity_entries:
                if not isinstance(activity, dict):
                    continue
                raw_locations.append(
                    {
                        "name": activity.get("location") or activity.get("activity"),
                        "district": activity.get("district"),
                        "block": activity.get("block"),
                    }
                )

        normalized_locations: list[dict[str, Any]] = []
        for raw_location in raw_locations:
            if isinstance(raw_location, str):
                location_name = _as_text(raw_location)
                if location_name:
                    normalized_locations.append({"name": location_name})
                continue

            if not isinstance(raw_location, dict):
                continue

            location_name = (
                _as_text(raw_location.get("name"))
                or _as_text(raw_location.get("location"))
                or _as_text(raw_location.get("place"))
                or _as_text(raw_location.get("activity"))
            )
            if not location_name:
                continue

            normalized_locations.append(
                {
                    "name": location_name,
                    "district": _as_text(raw_location.get("district")),
                    "block": _as_text(raw_location.get("block")),
                    "connectivity_zone": _as_text(raw_location.get("connectivity_zone"))
                    or _as_text(raw_location.get("connectivityZone")),
                    "assumed_location_risk": _as_text(raw_location.get("assumed_location_risk"))
                    or _as_text(raw_location.get("location_risk")),
                }
            )

        normalized_days.append(
            {
                "date": date_value,
                "locations": normalized_locations,
                "accommodation": _as_text(raw_day.get("accommodation"))
                or _as_text(raw_day.get("stay"))
                or _as_text(raw_day.get("hotel")),
            }
        )

    return {
        "days": normalized_days,
        "meta": root.get("meta") if isinstance(root.get("meta"), dict) else {},
    }


@trips_bp.post("")
def create_trip_route():
    """Create trip shell before itinerary analysis and monitoring begin."""
    try:
        payload = TripCreateSchema.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid trip payload", "details": exc.errors()}), 400

    created = create_trip(payload)
    return jsonify(created), 201


@trips_bp.get("")
def list_trips_route():
    """List trips for a user (expects `user_id` query parameter)."""
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400

    trips = list_trips_by_user(user_id)
    return jsonify({"items": trips})


@trips_bp.put("/<trip_id>/itinerary")
def update_itinerary_route(trip_id: str):
    """Store normalized itinerary data for a trip."""
    try:
        itinerary = ItinerarySchema.model_validate(request.get_json(force=True)).model_dump()
    except ValidationError as exc:
        return jsonify({"error": "invalid itinerary payload", "details": exc.errors()}), 400

    try:
        record = upsert_itinerary(trip_id, itinerary)
    except RuntimeError as exc:
        logger.warning("Skipping itinerary persistence for trip %s: %s", trip_id, exc)
        return jsonify({"trip_id": trip_id, **itinerary, "meta": {**itinerary.get("meta", {}), "saved": False}}), 200
    return jsonify(record)


@trips_bp.get("/<trip_id>/itinerary")
def get_itinerary_route(trip_id: str):
    """Return itinerary used by risk analysis and heartbeat tasks."""
    try:
        itinerary = get_itinerary(trip_id)
    except RuntimeError as exc:
        logger.warning("Skipping itinerary fetch for trip %s: %s", trip_id, exc)
        return jsonify({"trip_id": trip_id, "days": [], "meta": {"saved": False, "degraded": True}}), 200
    return jsonify(itinerary)


@trips_bp.post("/upload-pdf")
def upload_pdf_route():
    """Upload itinerary file and extract itinerary JSON using AI parsing.
    
    Expected form data:
    - trip_id: Trip identifier
    - file: itinerary document (.pdf/.docx/.txt/.doc)
    
    Returns: { "days": [...], "meta": {} }
    """
    try:
        trip_id = request.form.get("trip_id")
        if not trip_id:
            return jsonify({"error": "trip_id is required"}), 400
        
        if "file" not in request.files:
            return jsonify({"error": "file is required"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "file is empty"}), 400
        
        allowed_extensions = {".pdf", ".docx", ".txt", ".doc"}
        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in allowed_extensions:
            return jsonify({"error": "file must be one of: .pdf, .docx, .txt, .doc"}), 400
        
        # Save file to temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension or ".tmp") as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        try:
            # Extract itinerary from PDF
            logger.info(f"Extracting itinerary from uploaded document for trip {trip_id}")
            itinerary = extract_itinerary_from_document(temp_path)
            itinerary = _normalize_itinerary_payload(itinerary)
            itinerary = ItinerarySchema.model_validate(itinerary).model_dump()
            logger.info("[ItineraryParser] Normalized upload output: %s", itinerary)
            
            # Optionally save to database
            saved = False
            if itinerary.get("days"):
                try:
                    upsert_itinerary(trip_id, itinerary)
                    saved = True
                    logger.info(f"Saved extracted itinerary for trip {trip_id}")
                except Exception as save_error:
                    logger.warning(
                        "Could not persist extracted itinerary for trip %s; returning parsed data only: %s",
                        trip_id,
                        save_error,
                    )
            itinerary.setdefault("meta", {})
            itinerary["meta"]["saved"] = saved
            
            return jsonify(itinerary), 200
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"Itinerary document upload error: {e}")
        return jsonify({"error": f"Failed to process itinerary file: {str(e)}"}), 500


@trips_bp.post("/parse-text")
def parse_text_route():
    """Convert raw itinerary text into structured itinerary JSON.

    Expected JSON body:
    - trip_id: Trip identifier (optional, used for persistence)
    - itinerary_text: Raw text extracted from any source
    """
    try:
        payload = request.get_json(force=True) or {}
        trip_id = str(payload.get("trip_id") or "").strip()
        itinerary_text = str(payload.get("itinerary_text") or "").strip()

        if not itinerary_text:
            return jsonify({"error": "itinerary_text is required"}), 400

        itinerary = extract_itinerary_from_text(itinerary_text)
        itinerary = _normalize_itinerary_payload(itinerary)
        itinerary = ItinerarySchema.model_validate(itinerary).model_dump()
        logger.info("[ItineraryParser] Normalized text output: %s", itinerary)
        saved = False
        if trip_id and itinerary.get("days"):
            try:
                upsert_itinerary(trip_id, itinerary)
                saved = True
            except Exception as save_error:
                logger.warning(
                    "Could not persist parsed text itinerary for trip %s; returning parsed data only: %s",
                    trip_id,
                    save_error,
                )

        itinerary.setdefault("meta", {})
        itinerary["meta"]["saved"] = saved

        return jsonify(itinerary), 200
    except Exception as e:
        logger.error(f"Text parse error: {e}")
        return jsonify({"error": f"Failed to parse itinerary text: {str(e)}"}), 500
