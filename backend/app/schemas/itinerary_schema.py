"""Itinerary schema definitions.

Used by trip and analysis routes to validate day/location payloads.
"""

from pydantic import BaseModel, Field


class LocationSchema(BaseModel):
    """Single planned location with optional connectivity/risk hints."""

    name: str = Field(min_length=1)
    district: str | None = None
    block: str | None = None
    connectivity_zone: str | None = None
    assumed_location_risk: str | None = None


class DaySchema(BaseModel):
    """A day entry containing one or more locations and stay info."""

    date: str
    locations: list[LocationSchema] = Field(default_factory=list)
    accommodation: str | None = None


class ItinerarySchema(BaseModel):
    """Top-level itinerary payload validated at API boundary."""

    days: list[DaySchema] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
