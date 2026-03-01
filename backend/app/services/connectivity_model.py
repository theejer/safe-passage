"""Connectivity expectation model used by CURE monitoring.

Provides estimated offline windows for itinerary segments, which are
compared against heartbeat gaps in scheduled monitoring.
"""


def estimate_offline_window_minutes(location_or_segment: dict) -> int:
    """Return expected offline duration (minutes) for a location/route segment.

    This is intentionally simple for scaffold phase; production logic should
    incorporate tower density, route class, and historic reconnection patterns.
    """
    if location_or_segment.get("connectivity_zone") == "severe":
        return 180
    if location_or_segment.get("connectivity_zone") == "high":
        return 90
    if location_or_segment.get("connectivity_zone") == "moderate":
        return 45
    return 20


def should_trigger_alert(actual_offline_minutes: int, expected_offline_minutes: int) -> bool:
    """Risk-adaptive threshold placeholder to reduce false positives."""
    return actual_offline_minutes > int(expected_offline_minutes * 1.5)
