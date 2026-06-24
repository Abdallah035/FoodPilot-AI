"""Task 5 — unit tests for the scoring algorithm."""

from agent1_scout.scoring import (
    _credibility,
    price_to_tier,
    rank_top3,
    score_restaurant,
)
from agent1_scout.state import Coordinates, Restaurant

USER = {"lat": 29.9600, "lon": 31.2600}  # somewhere in Maadi


def _r(name, lat, lon, rating, reviews, price=None):
    return Restaurant(
        name=name,
        coordinates=Coordinates(lat=lat, lon=lon),
        rating=rating,
        reviews=reviews,
        price_level=price,
    )


# --- price tier normalisation ------------------------------------------------
def test_price_tier_from_range():
    assert price_to_tier("E£200–400") == "$"    # low bound 200 -> "$" (<=200)
    assert price_to_tier("E£100–150") == "$"
    assert price_to_tier("E£300–500") == "$$"   # low bound 300 -> "$$" (200<x<=500)
    assert price_to_tier("E£600–900") == "$$$"


def test_price_tier_passthrough_and_none():
    assert price_to_tier("$$") == "$$"
    assert price_to_tier(None) is None
    assert price_to_tier("no digits") is None


# --- credibility -------------------------------------------------------------
def test_credibility_rewards_reviews():
    many = _credibility(4.8, 5000)
    few = _credibility(4.8, 10)
    assert many > few  # same rating, more reviews -> more credible


def test_credibility_popular_place_not_punished():
    # a literal rating/reviews ratio would make this ~0; confidence-weighting keeps it high
    assert _credibility(4.8, 5000) > 0.85


# --- the spec's headline assertion ------------------------------------------
def test_near_established_beats_far_new():
    near_established = _r("Established", 29.961, 31.261, 4.6, 2000)  # ~0.1 km
    far_new = _r("BrandNew", 30.10, 31.40, 5.0, 1)                  # ~20 km
    a = score_restaurant(near_established, USER)
    b = score_restaurant(far_new, USER)
    assert a.score > b.score


def test_score_fields_filled():
    r = score_restaurant(_r("X", 29.961, 31.261, 4.5, 300), USER)
    assert r.distance_km is not None
    assert 0.0 <= r.score <= 1.0
    assert "★" in r.reason


def test_rank_top3_orders_and_limits():
    rs = [
        _r("A", 29.961, 31.261, 4.6, 2000),
        _r("B", 30.10, 31.40, 5.0, 1),
        _r("C", 29.962, 31.262, 4.2, 800),
        _r("D", 29.965, 31.265, 4.8, 50),
        _r("E", 29.970, 31.270, 4.0, 5000),
        _r("F", 30.20, 31.50, 4.9, 9000),
    ]
    top = rank_top3(rs, USER)
    assert len(top) == 3  # default top=3
    scores = [r.score for r in top]
    assert scores == sorted(scores, reverse=True)  # descending
    assert top[0].name == "A"  # near + well-reviewed wins
