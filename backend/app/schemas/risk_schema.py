"""Risk response schemas.

Services can validate generated risk payloads before persistence/response.
"""

from pydantic import BaseModel, Field


class LocationRiskSchema(BaseModel):
    """Risk values for one location/segment in a day."""

    name: str
    location_risk: str
    connectivity_risk: str
    expected_offline_minutes: int = Field(ge=0)


class DayRiskSchema(BaseModel):
    """Daily risk report chunk used by PREVENTION views."""

    date: str
    locations: list[LocationRiskSchema]


class RiskReportSchema(BaseModel):
    """Top-level risk report contract across service and API layers."""

    days: list[DayRiskSchema]
    summary: str
