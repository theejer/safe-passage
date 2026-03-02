"""Deterministic connectivity predictor from colocated signal metrics data.

This module is intentionally standalone and reusable. It does not wire itself
into routes or existing service flows.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from app.utils.geo import haversine_km, is_bihar_bbox

DATASET_PATH = Path(__file__).resolve().parent / "data" / "signal_metrics.csv"
DEFAULT_SIGNAL_RANGE = (-110.0, -75.0)
DEFAULT_THROUGHPUT_RANGE = (0.0, 100.0)
DEFAULT_LATENCY_RANGE = (10.0, 250.0)

NEIGHBOR_RADIUS_KM = 8.0
MIN_NEIGHBORS = 5
MAX_NEIGHBORS = 12
DISTANCE_EPSILON = 0.25


class ConnectivityPrediction(TypedDict):
    """Response contract for deterministic lat/lon connectivity prediction."""

    latitude: float
    longitude: float
    connectivity_score: float
    connectivity_group: str
    expected_connectivity: str
    expected_offline_minutes: int
    confidence: float
    data_points_used: int
    nearest_distance_km: float | None
    is_sparse: bool
    fallback_reason: str | None
    method: str


@dataclass(frozen=True)
class SignalRecord:
    """Minimal row shape needed for deterministic scoring."""

    latitude: float
    longitude: float
    signal_strength_dbm: float
    throughput_mbps: float
    latency_ms: float


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _range_or_default(values: list[float], default_range: tuple[float, float]) -> tuple[float, float]:
    if not values:
        return default_range
    min_value = min(values)
    max_value = max(values)
    if max_value <= min_value:
        return default_range
    return (min_value, max_value)


@lru_cache(maxsize=1)
def _load_signal_records(dataset_path: str | None = None) -> tuple[SignalRecord, ...]:
    path = Path(dataset_path) if dataset_path else DATASET_PATH
    if not path.exists():
        return ()

    records: list[SignalRecord] = []
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                records.append(
                    SignalRecord(
                        latitude=float(row["Latitude"]),
                        longitude=float(row["Longitude"]),
                        signal_strength_dbm=float(row["Signal Strength (dBm)"]),
                        throughput_mbps=float(row["Data Throughput (Mbps)"]),
                        latency_ms=float(row["Latency (ms)"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue

    return tuple(records)


@lru_cache(maxsize=1)
def _dataset_stats(dataset_path: str | None = None) -> dict[str, tuple[float, float]]:
    records = _load_signal_records(dataset_path)
    if not records:
        return {
            "signal": DEFAULT_SIGNAL_RANGE,
            "throughput": DEFAULT_THROUGHPUT_RANGE,
            "latency": DEFAULT_LATENCY_RANGE,
        }

    return {
        "signal": _range_or_default([record.signal_strength_dbm for record in records], DEFAULT_SIGNAL_RANGE),
        "throughput": _range_or_default([record.throughput_mbps for record in records], DEFAULT_THROUGHPUT_RANGE),
        "latency": _range_or_default([record.latency_ms for record in records], DEFAULT_LATENCY_RANGE),
    }


def _normalize_higher_better(value: float, value_range: tuple[float, float]) -> float:
    lower, upper = value_range
    if upper <= lower:
        return 0.5
    normalized = (value - lower) / (upper - lower)
    return _clamp(normalized)


def _normalize_lower_better(value: float, value_range: tuple[float, float]) -> float:
    return 1.0 - _normalize_higher_better(value, value_range)


def _record_sub_score(record: SignalRecord, stats: dict[str, tuple[float, float]]) -> float:
    signal_score = _normalize_higher_better(record.signal_strength_dbm, stats["signal"])
    throughput_score = _normalize_higher_better(record.throughput_mbps, stats["throughput"])
    latency_score = _normalize_lower_better(record.latency_ms, stats["latency"])
    return (signal_score * 0.45) + (throughput_score * 0.35) + (latency_score * 0.20)


def _group_for_score(score: float) -> str:
    rounded_score = int(round(score))
    if rounded_score >= 75:
        return "Excellent"
    if rounded_score >= 50:
        return "Good"
    if rounded_score >= 25:
        return "Average"
    return "Poor"


def _offline_minutes_for_score(score: float) -> int:
    bounded_score = _clamp(score, 0.0, 100.0)

    def _interpolate(score_value: float, x0: float, y0: float, x1: float, y1: float) -> float:
        if x1 <= x0:
            return y1
        ratio = (score_value - x0) / (x1 - x0)
        return y0 + (y1 - y0) * ratio

    if bounded_score <= 25.0:
        minutes = _interpolate(bounded_score, 0.0, 180.0, 25.0, 120.0)
    elif bounded_score <= 50.0:
        minutes = _interpolate(bounded_score, 25.0, 120.0, 50.0, 70.0)
    elif bounded_score <= 75.0:
        minutes = _interpolate(bounded_score, 50.0, 70.0, 75.0, 35.0)
    else:
        minutes = _interpolate(bounded_score, 75.0, 35.0, 100.0, 15.0)

    return int(round(_clamp(minutes, 15.0, 180.0)))


def _fallback_prediction(latitude: float, longitude: float, reason: str) -> ConnectivityPrediction:
    fallback_score = 20.0
    fallback_group = _group_for_score(fallback_score)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "connectivity_score": fallback_score,
        "connectivity_group": fallback_group,
        "expected_connectivity": fallback_group,
        "expected_offline_minutes": _offline_minutes_for_score(fallback_score),
        "confidence": 0.0,
        "data_points_used": 0,
        "nearest_distance_km": None,
        "is_sparse": True,
        "fallback_reason": reason,
        "method": "deterministic_weighted_neighborhood_v1",
    }


def _select_neighbors(
    records: tuple[SignalRecord, ...], latitude: float, longitude: float
) -> tuple[list[tuple[SignalRecord, float]], bool, str | None]:
    distance_pairs = [
        (record, haversine_km(latitude, longitude, record.latitude, record.longitude))
        for record in records
    ]
    distance_pairs.sort(key=lambda pair: pair[1])

    within_radius = [pair for pair in distance_pairs if pair[1] <= NEIGHBOR_RADIUS_KM][:MAX_NEIGHBORS]
    if len(within_radius) >= MIN_NEIGHBORS:
        return (within_radius, False, None)

    nearest = distance_pairs[:MAX_NEIGHBORS]
    if not nearest:
        return ([], True, "no_dataset_points")
    return (nearest, True, "sparse_local_neighborhood")


def _confidence_from_neighbors(neighbors: list[tuple[SignalRecord, float]], is_sparse: bool) -> float:
    if not neighbors:
        return 0.0

    nearest_distance = neighbors[0][1]
    proximity_factor = 1.0 - _clamp(nearest_distance / (NEIGHBOR_RADIUS_KM * 2.0))
    density_factor = _clamp(len(neighbors) / MAX_NEIGHBORS)
    sparse_penalty = 0.75 if is_sparse else 1.0
    confidence = proximity_factor * density_factor * sparse_penalty
    return round(_clamp(confidence), 3)


def predict_connectivity_for_latlon(latitude: float, longitude: float) -> ConnectivityPrediction:
    """Return deterministic connectivity score/group and expected offline minutes.

    Inputs:
    - latitude: decimal degrees
    - longitude: decimal degrees

    Outputs include:
    - connectivity_score (0-100)
    - connectivity_group and expected_connectivity in: Poor/Average/Good/Excellent
    - expected_offline_minutes (deterministic piecewise mapping)
    - fallback metadata for sparse/out-of-bounds/data-missing cases
    """
    if not is_bihar_bbox(latitude, longitude):
        return _fallback_prediction(latitude, longitude, "outside_bihar_bbox")

    records = _load_signal_records()
    if not records:
        return _fallback_prediction(latitude, longitude, "dataset_unavailable")

    stats = _dataset_stats()
    neighbors, is_sparse, fallback_reason = _select_neighbors(records, latitude, longitude)
    if not neighbors:
        return _fallback_prediction(latitude, longitude, fallback_reason or "no_dataset_points")

    weighted_sub_score_total = 0.0
    total_weight = 0.0
    for record, distance_km in neighbors:
        weight = 1.0 / (distance_km + DISTANCE_EPSILON)
        weighted_sub_score_total += _record_sub_score(record, stats) * weight
        total_weight += weight

    if total_weight <= 0:
        return _fallback_prediction(latitude, longitude, "invalid_neighbor_weights")

    score = round(_clamp(weighted_sub_score_total / total_weight) * 100.0, 2)
    group = _group_for_score(score)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "connectivity_score": score,
        "connectivity_group": group,
        "expected_connectivity": group,
        "expected_offline_minutes": _offline_minutes_for_score(score),
        "confidence": _confidence_from_neighbors(neighbors, is_sparse),
        "data_points_used": len(neighbors),
        "nearest_distance_km": round(neighbors[0][1], 3) if neighbors else None,
        "is_sparse": is_sparse,
        "fallback_reason": fallback_reason,
        "method": "deterministic_weighted_neighborhood_v1",
    }
