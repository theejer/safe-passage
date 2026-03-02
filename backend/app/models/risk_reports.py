"""Risk report data-access module.

Risk engine writes computed results here; trips/analysis routes read for clients.
"""

import json

from sqlalchemy import text

from app.extensions import get_db_engine


def save_risk_report(trip_id: str, report: dict) -> dict:
    """Persist risk output (location + connectivity risk summaries)."""
    query = text(
        """
        INSERT INTO risk_reports (trip_id, report)
        VALUES (:trip_id, CAST(:report AS jsonb))
        RETURNING *
        """
    )

    with get_db_engine().begin() as connection:
        row = connection.execute(
            query,
            {"trip_id": trip_id, "report": json.dumps(report)},
        ).mappings().first()

    return dict(row) if row else {}


def latest_risk_report(trip_id: str) -> dict:
    """Fetch latest risk report used by mobile PREVENTION views."""
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
        row = connection.execute(query, {"trip_id": trip_id}).mappings().first()

    return dict(row) if row else {}
