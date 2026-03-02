"""Tests for the connectivity_model service.

Covers:
- estimate_connectivity_rating returns value in [0, 100]
- well-connected urban location scores higher than remote rural location
- estimate_offline_minutes is inversely related to connectivity rating
- estimate_offline_minutes returns at minimum 5 minutes
- estimate_offline_window_minutes delegates to lat/lng path when provided
- estimate_offline_window_minutes falls back to zone heuristics
- should_trigger_alert threshold behaviour
"""

from __future__ import annotations

import pytest

from app.services.connectivity_model import (
    estimate_connectivity_rating,
    estimate_offline_minutes,
    estimate_offline_window_minutes,
    should_trigger_alert,
)

# Representative Bihar coordinates used across tests
_PATNA_LAT, _PATNA_LNG = 25.5941, 85.1376          # urban, strong 4G
_REMOTE_LAT, _REMOTE_LNG = 25.2000, 83.3500         # remote western Bihar, 2G


class TestEstimateConnectivityRating:
    def test_returns_float_in_valid_range(self):
        rating = estimate_connectivity_rating(_PATNA_LAT, _PATNA_LNG)
        assert 0.0 <= rating <= 100.0

    def test_urban_area_scores_higher_than_rural(self):
        urban = estimate_connectivity_rating(_PATNA_LAT, _PATNA_LNG)
        rural = estimate_connectivity_rating(_REMOTE_LAT, _REMOTE_LNG)
        assert urban > rural

    def test_rating_for_coordinates_outside_coverage_still_in_range(self):
        # Coordinates far outside Bihar dataset coverage
        rating = estimate_connectivity_rating(0.0, 0.0)
        assert 0.0 <= rating <= 100.0

    def test_rating_is_reproducible(self):
        r1 = estimate_connectivity_rating(_PATNA_LAT, _PATNA_LNG)
        r2 = estimate_connectivity_rating(_PATNA_LAT, _PATNA_LNG)
        assert r1 == r2


class TestEstimateOfflineMinutes:
    def test_returns_positive_integer(self):
        minutes = estimate_offline_minutes(_PATNA_LAT, _PATNA_LNG)
        assert isinstance(minutes, int)
        assert minutes >= 5

    def test_urban_area_shorter_offline_than_rural(self):
        urban_offline = estimate_offline_minutes(_PATNA_LAT, _PATNA_LNG)
        rural_offline = estimate_offline_minutes(_REMOTE_LAT, _REMOTE_LNG)
        assert urban_offline < rural_offline

    def test_minimum_is_five_minutes(self):
        # Even the best-rated location should return at least 5 minutes
        minutes = estimate_offline_minutes(_PATNA_LAT, _PATNA_LNG)
        assert minutes >= 5


class TestEstimateOfflineWindowMinutes:
    """Legacy API – must remain backward-compatible."""

    def test_zone_severe_returns_180(self):
        assert estimate_offline_window_minutes({"connectivity_zone": "severe"}) == 180

    def test_zone_high_returns_90(self):
        assert estimate_offline_window_minutes({"connectivity_zone": "high"}) == 90

    def test_zone_moderate_returns_45(self):
        assert estimate_offline_window_minutes({"connectivity_zone": "moderate"}) == 45

    def test_unknown_zone_returns_default(self):
        assert estimate_offline_window_minutes({}) == 20
        assert estimate_offline_window_minutes({"connectivity_zone": "unknown"}) == 20

    def test_delegates_to_lat_lng_when_provided(self):
        coord_result = estimate_offline_window_minutes(
            {"lat": _PATNA_LAT, "lng": _PATNA_LNG}
        )
        direct_result = estimate_offline_minutes(_PATNA_LAT, _PATNA_LNG)
        assert coord_result == direct_result

    def test_lat_lng_path_overrides_zone_key(self):
        """When lat/lng are present they take precedence over connectivity_zone."""
        result = estimate_offline_window_minutes(
            {"lat": _PATNA_LAT, "lng": _PATNA_LNG, "connectivity_zone": "severe"}
        )
        direct = estimate_offline_minutes(_PATNA_LAT, _PATNA_LNG)
        assert result == direct


class TestShouldTriggerAlert:
    def test_exceeds_threshold_triggers(self):
        assert should_trigger_alert(200, 100) is True

    def test_within_threshold_does_not_trigger(self):
        assert should_trigger_alert(140, 100) is False

    def test_exact_threshold_boundary_does_not_trigger(self):
        # 150 is exactly 1.5 × 100; should NOT trigger (strictly greater than)
        assert should_trigger_alert(150, 100) is False

    def test_one_above_threshold_triggers(self):
        assert should_trigger_alert(151, 100) is True
