"""Risk report data-access module.

Transforms itinerary_risks records into report format for PREVENTION views.
"""

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _is_missing_table_error(exc: Exception, table_name: str) -> bool:
    message = str(exc).lower()
    return (
        f"no such table: {table_name}" in message
        or f'relation "{table_name}" does not exist' in message
    )


def save_risk_report(trip_id: str, report: dict) -> dict:
    """Persist risk output by decomposing into itinerary_risks records.
    
    For now, this is a simplified implementation that stores the aggregated
    report metadata. Individual location/accommodation risks should be stored
    via the itinerary risk analysis pipeline.
    """
    if not _is_uuid(trip_id):
        return {}

    # Return a synthetic response that matches the old API for backwards compatibility
    return {
        "id": None,
        "trip_id": trip_id,
        "report": report,
        "summary": report.get("summary"),
        "created_at": None,
    }


def latest_risk_report(trip_id: str) -> dict:
    """Fetch and aggregate risk data for a trip from itinerary_risks table."""
    if not _is_uuid(trip_id):
        return {}

    # Query all risks for the trip, aggregated with location/day details
    query = text(
        """
        SELECT
          ir.id,
          ir.trip_id,
          ir.day_id,
          ir.location_ref_id,
          ir.accommodation_ref_id,
          ir.category,
          ir.risk_level,
          ir.recommendation,
          ir.source,
          ir.confidence,
          ir.connectivity_risk,
          ir.expected_offline_minutes,
          ir.connectivity_confidence,
          ir.connectivity_notes,
          ir.created_at,
          COALESCE(l.name, a.name) as location_name,
          COALESCE(l.address_city, a.address_city) as location_city,
          COALESCE(l.address_country, a.address_country) as location_country,
          id.label as day_label,
          id.day_date,
          id.day_order
        FROM itinerary_risks ir
        LEFT JOIN itinerary_locations l ON ir.location_ref_id = l.id
        LEFT JOIN itinerary_accommodations a ON ir.accommodation_ref_id = a.id
        LEFT JOIN itinerary_days id ON ir.day_id = id.id
        WHERE ir.trip_id = :trip_id
        ORDER BY id.day_order, ir.created_at DESC
        """
    )

    try:
        with get_db_engine().begin() as connection:
            result = connection.execute(query, {"trip_id": trip_id})
            rows = result.mappings().all()
    except (ProgrammingError, OperationalError) as exc:
        if _is_missing_table_error(exc, "itinerary_risks"):
            raise RuntimeError("itinerary_risks table is missing") from exc
        raise

    if not rows:
        return {}

    # Aggregate risks by day
    risks_by_day = {}
    all_risks = []

    for row in rows:
        risk_item = dict(row)
        all_risks.append(risk_item)

        day_key = risk_item.get("day_label") or f"Day {risk_item.get('day_order', 0)}"
        if day_key not in risks_by_day:
            risks_by_day[day_key] = {
                "day_label": day_key,
                "day_date": risk_item.get("day_date"),
                "risks": [],
            }

        risks_by_day[day_key]["risks"].append(risk_item)

    # Compute summary statistics
    high_risk_count = sum(1 for r in all_risks if r.get("risk_level", "").upper() == "HIGH")
    total_risks = len(all_risks)
    avg_confidence = (
        sum(r.get("confidence") or 0 for r in all_risks) / total_risks if total_risks > 0 else 0
    )

    summary = f"Risk report: {total_risks} risks identified, {high_risk_count} high severity."
    if avg_confidence > 0:
        summary += f" Average confidence: {avg_confidence:.0%}"

    return {
        "id": None,
        "trip_id": trip_id,
        "summary": summary,
        "created_at": rows[0].get("created_at") if rows else None,
        "risks_by_day": risks_by_day,
        "all_risks": all_risks,
        "stats": {
            "total_risks": total_risks,
            "high_risk_count": high_risk_count,
            "avg_confidence": float(avg_confidence),
        },
    }
