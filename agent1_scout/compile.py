"""Task 10 — State compilation: build the strict JSON output payload.

Turns the agreed-upon decisions (selected restaurant + selected deal + intent)
into the `OrderPayload` contract from the spec (§5), ready to hand to the next
agent in the pipeline.
"""

from __future__ import annotations

from .state import (
    Coordinates,
    Deal,
    OrderPayload,
    SelectedRestaurant,
)


def build_payload(
    user_intent: str,
    selected_restaurant: dict,
    selected_deal: dict,
) -> OrderPayload:
    """Assemble the OrderPayload from state dicts."""
    coords = selected_restaurant.get("coordinates") or {}
    restaurant = SelectedRestaurant(
        name=selected_restaurant["name"],
        address=selected_restaurant.get("address", ""),
        phone=selected_restaurant.get("phone", ""),
        coordinates=Coordinates(lat=coords["lat"], lon=coords["lon"]),
        google_maps_rating=selected_restaurant.get("rating", 0.0),
    )
    deal = Deal(**selected_deal)
    return OrderPayload(
        order_status="configured",
        user_intent=user_intent,
        selected_restaurant=restaurant,
        selected_deal=deal,
    )
