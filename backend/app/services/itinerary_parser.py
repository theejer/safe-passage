"""Itinerary parsing and normalization service.

Routes call this before risk analysis so downstream logic receives
consistent fields regardless of raw client formatting.
"""


def normalize_itinerary(itinerary_json: dict) -> dict:
    """Normalize itinerary payload into predictable schema shape.

    Interaction path:
    routes.itinerary_analysis -> services.itinerary_parser -> services.risk_engine
    """
    days = itinerary_json.get("days", [])
    normalized_days = []
    for day in days:
        normalized_days.append(
            {
                "date": day.get("date"),
                "locations": day.get("locations", []),
                "accommodation": day.get("accommodation"),
            }
        )

    return {"days": normalized_days, "meta": itinerary_json.get("meta", {})}
