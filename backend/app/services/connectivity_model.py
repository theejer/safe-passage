"""Connectivity expectation model used by CURE monitoring.

Provides lat/lng-based connectivity rating and expected offline window
estimates by querying a bundled Bihar cellular network dataset.

Dataset
-------
``app/services/data/cellular_network_data.csv`` is derived from Kaggle's
cellular network analysis dataset and contains representative signal
measurements across Bihar, India.  Columns:

- ``latitude``, ``longitude``       — measurement location
- ``signal_strength_dbm``            — RSSI in dBm (range −50 to −110)
- ``signal_quality_db``              — RSRQ in dB  (range −3 to −20)
- ``data_throughput_mbps``           — measured throughput (0.1–50 Mbps)
- ``latency_ms``                     — round-trip latency in ms
- ``network_type``                   — 2G / 3G / 4G / 5G

Usage
-----
::

    from app.services.connectivity_model import (
        estimate_connectivity_rating,
        estimate_offline_minutes,
    )

    # Patna city centre coordinates
    rating = estimate_connectivity_rating(25.5941, 85.1376)
    # → float in [0, 100]; higher is better

    offline = estimate_offline_minutes(25.5941, 85.1376)
    # → int; expected consecutive offline minutes for this location

    # Legacy helpers (used by risk_engine and heartbeat_monitor):
    window  = estimate_offline_window_minutes({"connectivity_zone": "high"})
    trigger = should_trigger_alert(120, window)
"""

from __future__ import annotations

import csv
import math
import os
from functools import lru_cache
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "cellular_network_data.csv")

_K_NEIGHBOURS = 5          # number of nearest data points used for weighting
_MAX_DISTANCE_KM = 100.0   # beyond this radius fall back to dataset-wide average


class _DataPoint(NamedTuple):
    lat: float
    lng: float
    signal_strength_dbm: float
    signal_quality_db: float
    data_throughput_mbps: float
    latency_ms: float
    network_type: str


@lru_cache(maxsize=1)
def _load_dataset() -> list[_DataPoint]:
    """Load and cache the cellular network CSV dataset."""
    points: list[_DataPoint] = []
    with open(_DATA_PATH, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                points.append(
                    _DataPoint(
                        lat=float(row["latitude"]),
                        lng=float(row["longitude"]),
                        signal_strength_dbm=float(row["signal_strength_dbm"]),
                        signal_quality_db=float(row["signal_quality_db"]),
                        data_throughput_mbps=float(row["data_throughput_mbps"]),
                        latency_ms=float(row["latency_ms"]),
                        network_type=row["network_type"].strip(),
                    )
                )
            except (KeyError, ValueError):
                continue  # skip malformed rows
    return points


# ---------------------------------------------------------------------------
# Internal geometry helpers
# ---------------------------------------------------------------------------

_EARTH_RADIUS_KM = 6371.0   # mean Earth radius used for Haversine distance
_EPSILON = 1e-9              # division-by-zero guard for inverse-distance weighting
_MAX_OFFLINE_BASE_MINUTES = 240.0  # offline minutes at connectivity rating = 0
_OFFLINE_CURVE_EXPONENT = 1.5      # power-curve shape for offline-time mapping
_MIN_OFFLINE_MINUTES = 5           # floor for estimated offline duration


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return great-circle distance in kilometres between two coordinates."""
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def _score_point(p: _DataPoint) -> float:
    """Compute connectivity rating [0–100] for a single dataset row.

    Weights:
    - Signal strength (40 %): −50 dBm → 100, −110 dBm → 0
    - Signal quality  (20 %): −3 dB  → 100, −20 dB  → 0
    - Throughput      (25 %): 50 Mbps → 100, 0 Mbps → 0
    - Latency         (15 %): 10 ms  → 100, 300 ms  → 0
    """
    ss = max(0.0, min(1.0, (p.signal_strength_dbm - (-110)) / (-50 - (-110)))) * 40.0
    sq = max(0.0, min(1.0, (p.signal_quality_db  - (-20))  / (-3  - (-20))))  * 20.0
    tp = max(0.0, min(1.0, p.data_throughput_mbps / 50.0))                    * 25.0
    lt = max(0.0, min(1.0, 1.0 - (p.latency_ms - 10.0) / (300.0 - 10.0)))   * 15.0
    return ss + sq + tp + lt


def _weighted_rating(lat: float, lng: float) -> float:
    """Return inverse-distance-weighted connectivity rating for (lat, lng)."""
    dataset = _load_dataset()

    # Compute (distance, score) for every row, then take K nearest
    scored = sorted(
        [(_haversine_km(lat, lng, p.lat, p.lng), _score_point(p)) for p in dataset],
        key=lambda x: x[0],
    )

    neighbours = [s for s in scored if s[0] <= _MAX_DISTANCE_KM][:_K_NEIGHBOURS]

    if not neighbours:
        # Coordinates are outside the dataset coverage area — fall back to mean
        return sum(s for _, s in scored[:_K_NEIGHBOURS]) / _K_NEIGHBOURS

    # Inverse-distance weighting; add tiny epsilon to avoid division by zero
    weights = [1.0 / (d + _EPSILON) for d, _ in neighbours]
    total_w = sum(weights)
    return sum(w * s for w, (_, s) in zip(weights, neighbours)) / total_w


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_connectivity_rating(lat: float, lng: float) -> float:
    """Return expected connectivity rating for the given coordinates.

    Parameters
    ----------
    lat:
        Latitude in decimal degrees.
    lng:
        Longitude in decimal degrees.

    Returns
    -------
    float
        Connectivity score in the range **[0, 100]**, where **100** represents
        the best possible connectivity and **0** represents no connectivity.
        The score is derived from signal strength, signal quality, data
        throughput, and latency measurements in the bundled dataset, using
        inverse-distance weighting over the *K* nearest data points.

    Examples
    --------
    ::

        # Patna – urban 4G area
        >>> estimate_connectivity_rating(25.5941, 85.1376)
        82.3   # (indicative value)

        # Remote rural area
        >>> estimate_connectivity_rating(25.2000, 83.3500)
        18.1   # (indicative value)
    """
    return round(_weighted_rating(lat, lng), 2)


def estimate_offline_minutes(lat: float, lng: float) -> int:
    """Return expected consecutive offline duration (minutes) for the given coordinates.

    The estimate uses an inverse power-curve mapping of the connectivity
    rating so that well-connected locations yield short offline windows while
    poorly-connected locations yield long offline windows:

    - Rating 100 → ~5 min   (virtually always online)
    - Rating  75 → ~33 min
    - Rating  50 → ~85 min
    - Rating  25 → ~155 min
    - Rating   0 → ~245 min (severely offline rural)

    Parameters
    ----------
    lat:
        Latitude in decimal degrees.
    lng:
        Longitude in decimal degrees.

    Returns
    -------
    int
        Expected offline window in minutes (minimum 5).

    Examples
    --------
    ::

        >>> estimate_offline_minutes(25.5941, 85.1376)
        12   # (indicative value)

        >>> estimate_offline_minutes(25.2000, 83.3500)
        190  # (indicative value)
    """
    rating = _weighted_rating(lat, lng)
    fraction_offline = 1.0 - rating / 100.0
    minutes = _MAX_OFFLINE_BASE_MINUTES * (fraction_offline ** _OFFLINE_CURVE_EXPONENT) + _MIN_OFFLINE_MINUTES
    return max(_MIN_OFFLINE_MINUTES, int(round(minutes)))


# ---------------------------------------------------------------------------
# Legacy helpers – kept for backward compatibility with risk_engine and
# heartbeat_monitor which pass a dict rather than coordinates.
# ---------------------------------------------------------------------------

def estimate_offline_window_minutes(location_or_segment: dict) -> int:
    """Return expected offline duration (minutes) for a location/route segment.

    Accepts a dict with either:

    - ``"lat"`` / ``"lng"`` keys  → delegates to :func:`estimate_offline_minutes`
    - ``"connectivity_zone"`` key → uses zone-based heuristic fallback

    If neither key is present the function returns a conservative default of
    20 minutes.
    """
    lat = location_or_segment.get("lat")
    lng = location_or_segment.get("lng")
    if lat is not None and lng is not None:
        return estimate_offline_minutes(float(lat), float(lng))

    zone = location_or_segment.get("connectivity_zone")
    if zone == "severe":
        return 180
    if zone == "high":
        return 90
    if zone == "moderate":
        return 45
    return 20


def should_trigger_alert(actual_offline_minutes: int, expected_offline_minutes: int) -> bool:
    """Return True when the actual gap exceeds 1.5× the expected window."""
    return actual_offline_minutes > int(expected_offline_minutes * 1.5)
