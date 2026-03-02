"""Risk report data-access module.

Risk engine writes computed results here; trips/analysis routes read for clients.
"""

import json
from uuid import UUID

from sqlalchemy import text

from app.extensions import get_db_engine


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def save_risk_report(trip_id: str, report: dict) -> dict:
    """Persist risk output (location + connectivity risk summaries)."""
    if not _is_uuid(trip_id):
        return {}

    query = text(
        """
        INSERT INTO risk_reports (trip_id, report, summary)
        VALUES (:trip_id, CAST(:report AS jsonb), :summary)
        RETURNING *
        """
    )
    with get_db_engine().begin() as connection:
        result = connection.execute(
            query,
            {
                "trip_id": trip_id,
                "report": json.dumps(report),
                "summary": report.get("summary"),
            },
        )
        row = result.mappings().first()
    return dict(row) if row else {}


def latest_risk_report(trip_id: str) -> dict:
    """Fetch latest risk report used by mobile PREVENTION views."""
    if not _is_uuid(trip_id):
        return {}

    query = text(
        """
        SELECT *
        FROM risk_reports
        WHERE trip_id = :trip_id
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    with get_db_engine().begin() as connection:
        result = connection.execute(query, {"trip_id": trip_id})
        row = result.mappings().first()
    return dict(row) if row else {}
