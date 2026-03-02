"""Trip and itinerary management routes.

These handlers orchestrate schema validation, model persistence,
and service operations for PREVENTION data setup.
"""

import os
import tempfile
from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.models.itineraries import get_itinerary, upsert_itinerary
from app.models.trips import create_trip, list_trips_by_user
from app.schemas.itinerary_schema import ItinerarySchema
from app.schemas.trip_schema import TripCreateSchema
from app.services.pdf_parser import extract_itinerary_from_pdf
from app.utils.logging import get_logger

logger = get_logger(__name__)
trips_bp = Blueprint("trips", __name__)


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

    record = upsert_itinerary(trip_id, itinerary)
    return jsonify(record)


@trips_bp.get("/<trip_id>/itinerary")
def get_itinerary_route(trip_id: str):
    """Return itinerary used by risk analysis and heartbeat tasks."""
    itinerary = get_itinerary(trip_id)
    return jsonify(itinerary)


@trips_bp.post("/upload-pdf")
def upload_pdf_route():
    """Upload PDF file and extract itinerary using AI parsing.
    
    Expected form data:
    - trip_id: Trip identifier
    - file: PDF file
    
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
        
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "file must be a PDF"}), 400
        
        # Save file to temp directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        try:
            # Extract itinerary from PDF
            logger.info(f"Extracting itinerary from PDF for trip {trip_id}")
            itinerary = extract_itinerary_from_pdf(temp_path)
            
            # Optionally save to database
            if itinerary.get("days"):
                upsert_itinerary(trip_id, itinerary)
                logger.info(f"Saved extracted itinerary for trip {trip_id}")
            
            return jsonify(itinerary), 200
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        logger.error(f"PDF upload error: {e}")
        return jsonify({"error": f"Failed to process PDF: {str(e)}"}), 500
