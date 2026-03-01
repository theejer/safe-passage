"""Risk scoring service for PREVENTION outputs.

This module combines itinerary data with connectivity/risk heuristics
and returns location + connectivity risk classifications.
"""

from app.services.connectivity_model import estimate_offline_window_minutes


def analyze_itinerary_risk(normalized_itinerary: dict) -> dict:
    """Generate minimal risk report per day/location.

    Interactions:
    - Consumes parser-normalized itinerary JSON
    - Uses connectivity model to estimate expected offline windows
    - Persists output via models.risk_reports in route layer
    """
    report_days = []
    for day in normalized_itinerary.get("days", []):
        day_locations = []
        for location in day.get("locations", []):
            offline_minutes = estimate_offline_window_minutes(location)
            connectivity_risk = "HIGH" if offline_minutes >= 120 else "MODERATE"
            location_risk = location.get("assumed_location_risk", "MODERATE")
            day_locations.append(
                {
                    "name": location.get("name"),
                    "location_risk": location_risk,
                    "connectivity_risk": connectivity_risk,
                    "expected_offline_minutes": offline_minutes,
                }
            )

        report_days.append({"date": day.get("date"), "locations": day_locations})

    return {"days": report_days, "summary": "Draft risk output; replace heuristics with live sources."}
