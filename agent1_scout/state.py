"""Task 1 — State schema for the Scout agent.

Defines the data that flows through the LangGraph graph (`ScoutState`) plus the
domain models (`Restaurant`, `Deal`) and the strict output contract
(`OrderPayload`) that matches the spec in 'Agent 1 - Discovery (Scout).md' §5.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from pydantic import BaseModel


# --------------------------------------------------------------------------- #
# Domain models
# --------------------------------------------------------------------------- #
class Coordinates(BaseModel):
    lat: float
    lon: float


class Restaurant(BaseModel):
    """A restaurant returned by Apify + enriched with our score."""

    name: str
    address: str = ""
    phone: str = ""  # from Apify Google Maps (formatted phone number)
    coordinates: Coordinates
    rating: float = 0.0  # Google Maps stars (0-5)
    reviews: int = 0  # total review count
    price_level: Optional[str] = None  # e.g. "$", "$$", "$$$"
    distance_km: Optional[float] = None  # filled by scoring
    score: Optional[float] = None  # filled by scoring (0-1)
    reason: Optional[str] = None  # short human-readable rank reason


class Deal(BaseModel):
    """A menu item / deal discovered via Tavily."""

    item_name: str
    price: str = ""
    currency: str = "EGP"
    deal_description: str = ""
    source_url: str = ""
    quantity: int = 1  # how many of this item the user wants
    portion: str = ""  # size / weight (e.g. "300g", "Large") — used later for calorie calc


# --------------------------------------------------------------------------- #
# Output contract (spec §5) — passed to the next agent
# --------------------------------------------------------------------------- #
class SelectedRestaurant(BaseModel):
    name: str
    address: str
    phone: str = ""
    coordinates: Coordinates
    google_maps_rating: float


class OrderPayload(BaseModel):
    order_status: str = "configured"
    user_intent: str
    selected_restaurant: SelectedRestaurant
    selected_deal: Deal


# --------------------------------------------------------------------------- #
# Graph state
# --------------------------------------------------------------------------- #
class ScoutState(TypedDict, total=False):
    """Mutable state threaded through the LangGraph nodes and interrupts."""

    # input
    user_query: str
    user_coords: dict  # {"lat": .., "lon": ..}
    location_query: str  # area text for Apify, e.g. "Maadi, Cairo"
    budget: Optional[str]  # "$" / "$$" / "$$$" or None

    # produced by intent parsing
    food_entity: str

    # produced by find_restaurants
    found_restaurants: list  # list[Restaurant] (as dicts in state)

    # set by HITL #1
    selected_restaurant: dict  # Restaurant

    # produced by find_deals
    found_deals: list  # list[Deal]

    # set when no menu/deals are found for selected_restaurant
    no_deals_action: str  # "show_info" | "choose_another"

    # set by HITL #2
    selected_deal: dict  # Deal

    # final output
    payload: dict  # OrderPayload
