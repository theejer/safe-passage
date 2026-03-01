"""Trip and itinerary management routes.

These handlers orchestrate schema validation, model persistence,
and service operations for PREVENTION data setup.
"""

from flask import Blueprint, jsonify, request

from app.models.itineraries import get_itinerary, upsert_itinerary
from app.models.trips import create_trip, list_trips_by_user
from app.schemas.itinerary_schema import ItinerarySchema
from app.schemas.trip_schema import TripCreateSchema

trips_bp = Blueprint("trips", __name__)


@trips_bp.post("")
def create_trip_route():
    """Create trip shell before itinerary analysis and monitoring begin."""
    payload = TripCreateSchema.model_validate(request.get_json(force=True)).model_dump()
    created = create_trip(payload)
    return jsonify(created), 201


@trips_bp.get("")
def list_trips_route():
    """List trips for a user (expects `user_id` query parameter)."""
    user_id = request.args.get("user_id", "")
    trips = list_trips_by_user(user_id)
    return jsonify({"items": trips})


@trips_bp.put("/<trip_id>/itinerary")
def update_itinerary_route(trip_id: str):
    """Store normalized itinerary data for a trip."""
    itinerary = ItinerarySchema.model_validate(request.get_json(force=True)).model_dump()
    record = upsert_itinerary(trip_id, itinerary)
    return jsonify(record)


@trips_bp.get("/<trip_id>/itinerary")
def get_itinerary_route(trip_id: str):
    """Return itinerary used by risk analysis and heartbeat tasks."""
    itinerary = get_itinerary(trip_id)
    return jsonify(itinerary)
