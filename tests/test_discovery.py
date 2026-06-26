"""Task 4 — tests for the Apify discovery tool.

Fast tests cover the result-mapping logic with a sample payload (offline).
A live actor-call test is gated behind RUN_APIFY=1 because it is slow and
consumes Apify credits.
"""

import os

import pytest

from agent1_scout import config
from agent1_scout.discovery import _coordinates_from_place, _map_place, geocode_location, search_restaurants
from agent1_scout.state import Coordinates, Restaurant

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


def test_coordinates_from_place_basic():
    coords = _coordinates_from_place(SAMPLE_PLACE)
    assert coords == Coordinates(lat=29.9601, lon=31.2569)


def test_coordinates_from_place_missing_coords_returns_none():
    assert _coordinates_from_place({"location": {}}) is None


def test_map_place_handles_missing_optional_fields():
    minimal = {"title": "Tiny Spot", "location": {"lat": 30.0, "lng": 31.0}}
    r = _map_place(minimal)
    assert r.name == "Tiny Spot"
    assert r.rating == 0.0
    assert r.reviews == 0
    assert r.price_level is None


def test_geocode_location_uses_apify_dataset(monkeypatch):
    calls = {}

    class FakeDataset:
        def iterate_items(self):
            yield {"location": {"lat": "29.9601", "lng": "31.2569"}}

    class FakeActor:
        def call(self, run_input):
            calls["run_input"] = run_input
            return {"defaultDatasetId": "dataset-1"}

    class FakeClient:
        def __init__(self, token):
            calls["token"] = token

        def actor(self, actor_id):
            calls["actor_id"] = actor_id
            return FakeActor()

        def dataset(self, dataset_id):
            calls["dataset_id"] = dataset_id
            return FakeDataset()

    monkeypatch.setattr(config, "APIFY_API_TOKEN", "token-1")
    monkeypatch.setattr("apify_client.ApifyClient", FakeClient)

    coords = geocode_location("Maadi, Cairo")

    assert coords == Coordinates(lat=29.9601, lon=31.2569)
    assert calls["token"] == "token-1"
    assert calls["actor_id"] == "compass/google-maps-extractor"
    assert calls["dataset_id"] == "dataset-1"
    assert calls["run_input"] == {
        "searchStringsArray": ["Maadi, Cairo"],
        "maxCrawledPlacesPerSearch": 1,
        "language": "en",
    }


def test_geocode_location_returns_none_without_usable_coords(monkeypatch):
    class FakeDataset:
        def iterate_items(self):
            yield {"location": {}}

    class FakeActor:
        def call(self, run_input):
            return {"defaultDatasetId": "dataset-1"}

    class FakeClient:
        def __init__(self, token):
            pass

        def actor(self, actor_id):
            return FakeActor()

        def dataset(self, dataset_id):
            return FakeDataset()

    monkeypatch.setattr(config, "APIFY_API_TOKEN", "token-1")
    monkeypatch.setattr("apify_client.ApifyClient", FakeClient)

    assert geocode_location("Unknown place") is None


@pytest.mark.skipif(os.getenv("RUN_APIFY") != "1", reason="set RUN_APIFY=1 to hit Apify")
def test_search_restaurants_live():
    results = search_restaurants("burger", "Maadi, Cairo", n=5)
    assert len(results) >= 1
    assert all(isinstance(r, Restaurant) for r in results)
    assert all(r.coordinates for r in results)


@pytest.mark.skipif(os.getenv("RUN_APIFY") != "1", reason="set RUN_APIFY=1 to hit Apify")
def test_geocode_location_live():
    coords = geocode_location("Maadi, Cairo")
    assert coords is not None
    assert 29.0 <= coords.lat <= 31.0
    assert 30.0 <= coords.lon <= 32.0
