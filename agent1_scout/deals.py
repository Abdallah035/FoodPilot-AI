"""Task 8 — Deal deep-dive (real + latest Egyptian menu prices).

Accurate strategy:
  1. Tavily (restricted to talabat.com) finds the restaurant's EXACT Talabat
     page URL, from which we extract the restaurant SLUG.
  2. Apify Talabat scraper with `restaurantSlugs=[slug]` scrapes that EXACT
     restaurant's live menu — deterministic, so we never get the wrong place
     (the old `queries` search returned a generic list and missed the real
     restaurant, e.g. "Primo's Pizza" -> a sushi bar).
  3. Items with no real price (0 / empty) are dropped; duplicates removed.

Fallbacks (Tavily open-web extract, then LLM estimate) live in Task 8b/8c.

This module: Task 8a — Tavily slug lookup + slug-based Talabat scrape.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from . import config
from .discovery import _dataset_id
from .state import Deal

TALABAT_ACTOR_ID = "thirdwatch/talabat-scraper"


# --------------------------------------------------------------------------- #
# Step 1 — find the exact Talabat slug via Tavily
# --------------------------------------------------------------------------- #
def slug_from_talabat_url(url: str) -> Optional[str]:
    """Extract the restaurant slug from a Talabat URL.

    Handles both:
      talabat.com/egypt/<slug>
      talabat.com/egypt/restaurant/<id>/<slug>?aid=...
    """
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    parts = [p for p in path.split("/") if p]
    # drop leading country segment(s) like 'egypt'
    # the slug is the last path segment that isn't a pure number
    for seg in reversed(parts):
        if seg in {"restaurant", "egypt"} or seg.isdigit():
            continue
        return seg
    return None


def find_talabat_slug(restaurant_name: str, max_results: int = 5) -> Optional[str]:
    """Use Tavily (talabat.com only) to find the restaurant's Talabat slug."""
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env.")

    from tavily import TavilyClient

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    resp = client.search(
        query=f"{restaurant_name} Talabat Egypt menu",
        max_results=max_results,
        search_depth="advanced",
        include_domains=["talabat.com"],
    )
    for result in resp.get("results", []):
        slug = slug_from_talabat_url(result.get("url", ""))
        if slug:
            return slug
    return None


# --------------------------------------------------------------------------- #
# Item mapping
# --------------------------------------------------------------------------- #
def _price_to_str(price) -> str:
    if price is None or isinstance(price, bool):
        return ""
    if isinstance(price, (int, float)):
        return str(int(price)) if float(price).is_integer() else str(price)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(price))
    return m.group(0).replace(",", "") if m else ""


def _has_real_price(price_str: str) -> bool:
    try:
        return float(price_str) > 0
    except (TypeError, ValueError):
        return False


def _map_menu_item(item: dict, food_entity: str = "") -> Optional[Deal]:
    name = item.get("name") or item.get("item_name")
    if not name:
        return None
    price = _price_to_str(item.get("price"))
    if not _has_real_price(price):
        return None  # skip template / 0-price rows
    return Deal(
        item_name=name.strip(),
        price=price,
        currency="EGP",
        deal_description=(item.get("description") or item.get("category") or "").strip(),
        source_url=item.get("url") or item.get("image") or "talabat.com",
        portion="",
    )


def _dedupe(deals: list[Deal]) -> list[Deal]:
    seen, out = set(), []
    for d in deals:
        key = (d.item_name.lower(), d.price)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def _filter_relevant(deals: list[Deal], food_entity: str) -> list[Deal]:
    """Keep deals whose name/description relate to the craving; else keep all."""
    if not food_entity:
        return deals
    tokens = [t for t in re.split(r"\s+", food_entity.lower()) if len(t) >= 2]
    if not tokens:
        return deals
    relevant = [
        d for d in deals
        if any(t in (d.item_name + " " + d.deal_description).lower() for t in tokens)
    ]
    return relevant or deals


# --------------------------------------------------------------------------- #
# Step 2 — scrape the exact restaurant by slug
# --------------------------------------------------------------------------- #
def talabat_menu_by_slug(
    slug: str,
    food_entity: str = "",
    country: str = "eg",
) -> list[Deal]:
    """Scrape one exact Talabat restaurant by slug; return clean menu Deals."""
    if not config.APIFY_API_TOKEN:
        raise RuntimeError("APIFY_API_TOKEN is not set. Add it to your .env.")

    from apify_client import ApifyClient

    client = ApifyClient(config.APIFY_API_TOKEN)
    run = client.actor(TALABAT_ACTOR_ID).call(
        run_input={
            "restaurantSlugs": [slug],
            "country": country,
            "scrapeMenu": True,
            "maxResults": 1,
        }
    )

    deals: list[Deal] = []
    for restaurant in client.dataset(_dataset_id(run)).iterate_items():
        for item in restaurant.get("menu_items", []) or []:
            d = _map_menu_item(item, food_entity)
            if d is not None:
                deals.append(d)

    return _filter_relevant(_dedupe(deals), food_entity)


def talabat_menu(
    restaurant_name: str,
    food_entity: str = "",
    country: str = "eg",
) -> list[Deal]:
    """Accurate Talabat menu: Tavily finds the slug, then we scrape that slug.

    Returns [] if no Talabat page is found (caller falls back to Tavily web
    extract / LLM estimate).
    """
    slug = find_talabat_slug(restaurant_name)
    if not slug:
        return []
    return talabat_menu_by_slug(slug, food_entity, country)


# --------------------------------------------------------------------------- #
# Task 8d — public orchestrator: Talabat -> Tavily web -> estimate
# --------------------------------------------------------------------------- #
def find_deals(
    restaurant_name: str,
    food_entity: str = "",
    country: str = "eg",
    limit: int = 12,
) -> list[Deal]:
    """Get the best available menu deals for a restaurant.

    1. Talabat by slug (live, authoritative).
    2. If empty, Tavily open-web fallback.
    3. Fill any missing prices with a flagged LLM estimate.

    Returns at most `limit` deals (so the user isn't overwhelmed at selection).
    """
    from .deals_estimate import estimate_missing_prices
    from .deals_fallback import tavily_menu_fallback

    deals = talabat_menu(restaurant_name, food_entity, country)
    if not deals:
        deals = tavily_menu_fallback(restaurant_name, food_entity)

    # estimate any still-missing prices (mostly affects the web fallback path)
    deals = estimate_missing_prices(deals, restaurant_name)

    return deals[:limit]
