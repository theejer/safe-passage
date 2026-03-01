"""Geospatial helpers.

Shared by risk engine and monitoring tasks for distance/region operations.
"""

from math import asin, cos, radians, sin, sqrt


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in kilometers between two points."""
    radius_km = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius_km * c


def is_bihar_bbox(lat: float, lon: float) -> bool:
    """Coarse bounding-box check for Bihar-focused logic defaults."""
    return 24.0 <= lat <= 27.6 and 83.2 <= lon <= 88.3
