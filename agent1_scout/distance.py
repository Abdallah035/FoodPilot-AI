"""Task 3 — Haversine distance calculator (pure Python, no API).

Computes the great-circle distance in kilometres between the user's coordinates
and a restaurant's coordinates. Used by the scoring algorithm (proximity, 40%).
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0


def haversine(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance between two (lat, lon) points, in kilometres."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_KM * c


def haversine_coords(a: dict, b: dict) -> float:
    """Convenience wrapper for two {'lat':.., 'lon':..} dicts."""
    return haversine(a["lat"], a["lon"], b["lat"], b["lon"])
