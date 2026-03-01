"""Risk report data-access module.

Risk engine writes computed results here; trips/analysis routes read for clients.
"""

from app.extensions import get_supabase


def save_risk_report(trip_id: str, report: dict) -> dict:
    """Persist risk output (location + connectivity risk summaries)."""
    response = get_supabase().table("risk_reports").insert({"trip_id": trip_id, "report": report}).execute()
    return response.data[0] if response.data else {}


def latest_risk_report(trip_id: str) -> dict:
    """Fetch latest risk report used by mobile PREVENTION views."""
    response = (
        get_supabase()
        .table("risk_reports")
        .select("*")
        .eq("trip_id", trip_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else {}
