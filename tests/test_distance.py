"""Task 3 — unit tests for the Haversine distance calculator."""

from agent1_scout.distance import haversine, haversine_coords


def test_zero_distance():
    assert haversine(31.2, 29.9, 31.2, 29.9) == 0.0


def test_known_distance_cairo_alexandria():
    # Cairo (30.0444, 31.2357) -> Alexandria (31.2001, 29.9187)
    # Real great-circle distance is ~180 km.
    d = haversine(30.0444, 31.2357, 31.2001, 29.9187)
    assert 175 <= d <= 185


def test_symmetry():
    a = haversine(30.0444, 31.2357, 31.2001, 29.9187)
    b = haversine(31.2001, 29.9187, 30.0444, 31.2357)
    assert abs(a - b) < 1e-9


def test_coords_wrapper_matches():
    a = haversine(30.0, 31.0, 30.1, 31.1)
    b = haversine_coords({"lat": 30.0, "lon": 31.0}, {"lat": 30.1, "lon": 31.1})
    assert a == b


def test_nearer_is_smaller():
    user = (30.0444, 31.2357)
    near = haversine(*user, 30.05, 31.24)   # ~1 km
    far = haversine(*user, 30.15, 31.34)    # ~15 km
    assert near < far
