"""Task 5 — Scoring algorithm.

Weighted score (0-1) used to rank restaurants before showing the top 5:

    Proximity    40%  inversely proportional to distance (1 km >> 10 km)
    Credibility  50%  rating AND review count together — a confidence-weighted
                      rating: (rating/5) * min(1, log10(reviews+1)/4).
                      High only when the rating is high AND backed by many
                      reviews. (Replaces the old separate quality + reliability.)
    Price match  10%  alignment with the user's budget tier

Apify returns `price_level` as a currency range string (e.g. "E£200–400"),
so we normalise it into a $/$$/$$$ tier before matching the user's budget.
"""

from __future__ import annotations

import math
import re
from typing import Optional

import config
from .distance import haversine_coords
from .state import Restaurant

# weights
W_PROXIMITY = 0.40
W_CREDIBILITY = 0.50
W_PRICE = 0.10

# Budget tier thresholds (lower bound of the price range, in EGP). Tunable.
_TIER1_MAX = 200   # <=200 -> "$"
_TIER2_MAX = 500   # <=500 -> "$$"  ; >500 -> "$$$"


def price_to_tier(price_level: Optional[str]) -> Optional[str]:
    """Normalise a raw price string into '$' / '$$' / '$$$' (or None)."""
    if not price_level:
        return None
    if price_level and set(price_level) <= {"$"}:  # already a tier
        return price_level
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", price_level)]
    if not nums:
        return None
    low = min(nums)
    if low <= _TIER1_MAX:
        return "$"
    if low <= _TIER2_MAX:
        return "$$"
    return "$$$"


def _proximity(distance_km: float, max_dist_km: float) -> float:
    return max(0.0, 1.0 - distance_km / max_dist_km)


def _credibility(rating: float, reviews: int) -> float:
    """Confidence-weighted rating: high only when rating AND reviews are high."""
    rating_norm = max(0.0, min(1.0, rating / 5.0))
    confidence = min(1.0, math.log10(reviews + 1) / 4.0)  # ~10k reviews -> 1.0
    return rating_norm * confidence


def _price_match(restaurant_tier: Optional[str], budget: Optional[str]) -> float:
    if budget is None or restaurant_tier is None:
        return 0.5  # neutral when we can't compare
    return 1.0 if restaurant_tier == budget else 0.0


def score_restaurant(
    r: Restaurant,
    user_coords: dict,
    budget: Optional[str] = None,
    max_dist_km: Optional[float] = None,
) -> Restaurant:
    """Return a copy of `r` with distance_km, score and reason filled in."""
    max_dist_km = max_dist_km or config.MAX_DISTANCE_KM

    distance = haversine_coords(user_coords, r.coordinates.model_dump())
    tier = price_to_tier(r.price_level)

    proximity = _proximity(distance, max_dist_km)
    credibility = _credibility(r.rating, r.reviews)
    price_match = _price_match(tier, budget)

    score = W_PROXIMITY * proximity + W_CREDIBILITY * credibility + W_PRICE * price_match

    reason = (
        f"{r.rating}★ ({r.reviews} reviews), {distance:.1f} km away"
        + (f", {tier}" if tier else "")
    )

    return r.model_copy(
        update={
            "distance_km": round(distance, 2),
            "score": round(score, 4),
            "reason": reason,
        }
    )


def rank_top3(
    restaurants: list[Restaurant],
    user_coords: dict,
    budget: Optional[str] = None,
    max_dist_km: Optional[float] = None,
    top: int = 3,
) -> list[Restaurant]:
    """Score every restaurant and return the highest-scoring `top` of them."""
    scored = [
        score_restaurant(r, user_coords, budget, max_dist_km) for r in restaurants
    ]
    scored.sort(key=lambda r: r.score or 0.0, reverse=True)
    return scored[:top]
