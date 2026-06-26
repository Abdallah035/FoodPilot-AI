"""Task 4 — Apify discovery tool.

Calls the Apify **Google Maps Extractor** actor (`compass/google-maps-extractor`)
to find restaurants matching the food entity in the user's area, and maps the
raw results into our `Restaurant` model.

Actor input we use:
    searchStringsArray         -> ["<food entity> restaurant"]
    locationQuery              -> "<area text>"   (e.g. "Maadi, Cairo")
    maxCrawledPlacesPerSearch  -> how many to pull

Relevant raw output fields (per place):
    title, totalScore, reviewsCount, location.{lat,lng}, address, phone, price
"""

from __future__ import annotations

from typing import Optional

import config
from .state import Coordinates, Restaurant

ACTOR_ID = "compass/google-maps-extractor"


def _dataset_id(run) -> str:
    """Get the default dataset id from a Run (dict in some versions, object in others)."""
    if isinstance(run, dict):
        return run["defaultDatasetId"]
    # apify-client v3 returns a Run object
    return getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]


def _map_place(place: dict) -> Optional[Restaurant]:
    """Convert one raw Apify place dict into a Restaurant (or None if unusable)."""
    coords = _coordinates_from_place(place)
    if coords is None:
        return None  # we need coordinates for distance scoring

    return Restaurant(
        name=place.get("title") or "Unknown",
        address=place.get("address") or "",
        phone=place.get("phone") or place.get("phoneUnformatted") or "",
        coordinates=coords,
        rating=float(place.get("totalScore") or 0.0),
        reviews=int(place.get("reviewsCount") or 0),
        price_level=place.get("price"),  # e.g. "$$" or None
    )


def _coordinates_from_place(place: dict) -> Optional[Coordinates]:
    """Extract coordinates from one raw Apify place dict."""
    loc = place.get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    return Coordinates(lat=float(lat), lon=float(lng))


def geocode_location(location_query: str) -> Optional[Coordinates]:
    """Resolve a location text query to coordinates using the Apify Maps actor."""
    if not config.APIFY_API_TOKEN:
        raise RuntimeError(
            "APIFY_API_TOKEN is not set. Add it to your .env or pass --lat and --lon explicitly."
        )

    from apify_client import ApifyClient

    client = ApifyClient(config.APIFY_API_TOKEN)
    run_input = {
        "searchStringsArray": [location_query],
        "maxCrawledPlacesPerSearch": 1,
        "language": "en",
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    dataset_id = _dataset_id(run)

    for item in client.dataset(dataset_id).iterate_items():
        coords = _coordinates_from_place(item)
        if coords is not None:
            return coords

    return None


def search_restaurants(
    food_entity: str,
    location_query: str,
    n: int = 10,
) -> list[Restaurant]:
    """Find up to `n` restaurants for `food_entity` near `location_query`.

    Raises if APIFY_API_TOKEN is missing or the actor run fails — we do not mock.
    """
    if not config.APIFY_API_TOKEN:
        raise RuntimeError(
            "APIFY_API_TOKEN is not set. Add it to your .env to search restaurants."
        )

    from apify_client import ApifyClient

    client = ApifyClient(config.APIFY_API_TOKEN)
    # Bake the location into the search string and DO NOT set locationQuery:
    # the actor's locationQuery polygon can be computed too small and filter
    # out every result ("outOfLocation"). Search-string mode is reliable.
    run_input = {
        "searchStringsArray": [f"{food_entity} restaurant {location_query}"],
        "maxCrawledPlacesPerSearch": n,
        "skipClosedPlaces": True,
        "language": "en",
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    dataset_id = _dataset_id(run)

    restaurants: list[Restaurant] = []
    for item in client.dataset(dataset_id).iterate_items():
        r = _map_place(item)
        if r is not None:
            restaurants.append(r)
        if len(restaurants) >= n:
            break

    return restaurants
