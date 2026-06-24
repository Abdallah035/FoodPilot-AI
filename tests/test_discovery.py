"""Task 4 — tests for the Apify discovery tool.

Fast tests cover the result-mapping logic with a sample payload (offline).
A live actor-call test is gated behind RUN_APIFY=1 because it is slow and
consumes Apify credits.
"""

import os

import pytest

from agent1_scout import config
from agent1_scout.discovery import _map_place, search_restaurants
from agent1_scout.state import Restaurant

# A trimmed sample of the Apify Google Maps Extractor output.
SAMPLE_PLACE = {
    "title": "Burger House",
    "address": "12 Road 9, Maadi, Cairo",
    "location": {"lat": 29.9601, "lng": 31.2569},
    "totalScore": 4.6,
    "reviewsCount": 2034,
    "price": "$$",
}


def test_map_place_basic():
    r = _map_place(SAMPLE_PLACE)
    assert isinstance(r, Restaurant)
    assert r.name == "Burger House"
    assert r.rating == 4.6
    assert r.reviews == 2034
    assert r.price_level == "$$"
    assert r.coordinates.lat == 29.9601
    assert r.coordinates.lon == 31.2569


def test_map_place_missing_coords_returns_none():
    bad = dict(SAMPLE_PLACE)
    bad["location"] = {}
    assert _map_place(bad) is None


def test_map_place_handles_missing_optional_fields():
    minimal = {"title": "Tiny Spot", "location": {"lat": 30.0, "lng": 31.0}}
    r = _map_place(minimal)
    assert r.name == "Tiny Spot"
    assert r.rating == 0.0
    assert r.reviews == 0
    assert r.price_level is None


@pytest.mark.skipif(os.getenv("RUN_APIFY") != "1", reason="set RUN_APIFY=1 to hit Apify")
def test_search_restaurants_live():
    results = search_restaurants("burger", "Maadi, Cairo", n=5)
    assert len(results) >= 1
    assert all(isinstance(r, Restaurant) for r in results)
    assert all(r.coordinates for r in results)
