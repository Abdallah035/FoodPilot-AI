"""Task 6 — tests for the find_restaurants node.

These exercise the node with **Egyptian Arabic** queries. The real Azure OpenAI
intent parser runs (so the Arabic NLU path is genuinely tested); only the Apify network
scraper is mocked with a realistic set of Maadi restaurants. A fully-live test is
gated behind RUN_LIVE=1.
"""

import pytest

import config
from agent1_scout import nodes
from agent1_scout.state import Coordinates, Restaurant

requires_azure = pytest.mark.skipif(not config.has_azure_openai(), reason="Azure OpenAI is not configured")

# user standing in Maadi
USER = {"lat": 29.9600, "lon": 31.2600}
LOCATION = "المعادي، القاهرة"  # "Maadi, Cairo" in Arabic


def _r(name, lat, lon, rating, reviews, price=None):
    return Restaurant(
        name=name, coordinates=Coordinates(lat=lat, lon=lon),
        rating=rating, reviews=reviews, price_level=price,
    )


# A realistic Maadi line-up (Arabic names), as Apify would return them.
KOFTA_PLACES = [
    _r("الشبراوي", 29.9610, 31.2615, 4.3, 5200, "E£100–200"),   # near, huge reviews, cheap
    _r("مطعم الكبابجي", 29.9700, 31.2700, 4.7, 1800, "E£300–500"),  # a bit far, great rating
    _r("كشري وكفتة التحرير", 29.9590, 31.2590, 4.1, 90, "E£50–150"),  # very near, few reviews
    _r("جراند كفتة", 30.0500, 31.3500, 4.9, 30, "E£600–900"),   # far, almost no reviews, pricey
    _r("كفتة ستيشن", 29.9650, 31.2650, 4.5, 760, "E£200–400"),  # near-ish, solid
]

PIZZA_PLACES = [
    _r("بيتزا كينج", 29.9605, 31.2610, 4.0, 3000, "E£80–150"),   # near + cheap + popular
    _r("Maestro Pizza", 29.9620, 31.2630, 4.6, 220, "E£250–450"),
    _r("بيتزا هت المعادي", 29.9900, 31.2900, 4.2, 1500, "E£200–500"),
]


@requires_azure
def test_arabic_kofta_pipeline(monkeypatch):
    """عايز كفتة كويسة -> kofta intent, near + well-reviewed place wins."""
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: KOFTA_PLACES)

    state = {
        "user_query": "عايز كفتة كويسة",
        "user_coords": USER,
        "location_query": LOCATION,
    }
    out = nodes.find_restaurants(state)

    # intent stayed Arabic and is about kofta
    assert "كفت" in out["food_entity"]
    # top 3 returned, scored, descending
    top = out["found_restaurants"]
    assert len(top) == 3
    scores = [r["score"] for r in top]
    assert scores == sorted(scores, reverse=True)
    # the far, 30-review, pricey "جراند كفتة" must NOT be #1 despite its 4.9 rating
    assert top[0]["name"] != "جراند كفتة"
    # every result carries a distance + human reason
    assert all(r["distance_km"] is not None for r in top)
    assert all("★" in r["reason"] for r in top)


@requires_azure
def test_arabic_cheap_pizza_budget(monkeypatch):
    """أرخص بيتزا -> budget '$' inferred, cheap near place favoured."""
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: PIZZA_PLACES)

    state = {
        "user_query": "أرخص بيتزا في المنطقة",
        "user_coords": USER,
        "location_query": LOCATION,
    }
    out = nodes.find_restaurants(state)

    assert out["budget"] == "$"  # budget came from the Arabic intent
    assert "بيتزا" in out["food_entity"] or "pizza" in out["food_entity"].lower()
    # the cheap, near, popular "بيتزا كينج" should rank first
    assert out["found_restaurants"][0]["name"] == "بيتزا كينج"


@pytest.mark.skipif(not config.RUN_LIVE, reason="set RUN_LIVE=1 for full live run")
def test_arabic_kofta_fully_live():
    """End-to-end with real Azure OpenAI + real Apify on an Arabic craving."""
    state = {
        "user_query": "عايز كفتة",
        "user_coords": USER,
        "location_query": "Maadi, Cairo",
    }
    out = nodes.find_restaurants(state)
    assert "كفت" in out["food_entity"]
    assert 1 <= len(out["found_restaurants"]) <= 3
