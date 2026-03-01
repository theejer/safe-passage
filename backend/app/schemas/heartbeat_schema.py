"""Heartbeat request schemas.

Used by heartbeat routes to validate ingest payloads from mobile clients.
"""

from typing import Literal

from pydantic import BaseModel, Field


class HeartbeatGpsSchema(BaseModel):
    """Nested GPS payload for heartbeat events."""

    lat: float
    lng: float
    accuracy_meters: float | None = None


class HeartbeatIngestSchema(BaseModel):
    """Validated heartbeat payload contract for CURE monitoring."""

    user_id: str = Field(min_length=1)
    trip_id: str = Field(min_length=1)
    timestamp: str
    gps: HeartbeatGpsSchema | None = None
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    network_status: Literal["online", "offline", "unknown"] = "unknown"
    offline_minutes: int | None = Field(default=None, ge=0)
    source: Literal["background_fetch", "manual_debug", "foreground"] = "background_fetch"
    emergency_phone: str | None = None
