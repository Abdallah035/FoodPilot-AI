"""Task 6+ — LangGraph nodes for the Scout agent.

Each node takes the current ScoutState and returns a partial state update.
"""

from __future__ import annotations

from langgraph.types import interrupt

from .compile import build_payload
from .deals import find_deals
from .discovery import search_restaurants
from .intent import parse_intent
from .scoring import rank_top3
from .state import ScoutState


def find_restaurants(state: ScoutState) -> dict:
    """Node: intent parse -> Apify discovery -> score -> top 3.

    Reads:  user_query, user_coords, location_query, (optional) budget
    Writes: food_entity, budget, found_restaurants (top 3, as dicts)
    """
    user_query = state["user_query"]
    user_coords = state["user_coords"]
    location_query = state["location_query"]

    # 1. parse intent (food entity + budget) — Arabic or English
    intent = parse_intent(user_query)
    budget = state.get("budget") or intent.budget

    # 2. broad discovery via Apify
    restaurants = search_restaurants(intent.food_entity, location_query, n=5)

    # 3. score + rank, keep top 3
    top = rank_top3(restaurants, user_coords, budget=budget)

    return {
        "food_entity": intent.food_entity,
        "budget": budget,
        "found_restaurants": [r.model_dump() for r in top],
    }


def ask_user_restaurant(state: ScoutState) -> dict:
    """HITL #1: pause and let the user pick one of the top restaurants.

    Calls interrupt() with the options payload. The graph freezes here; the
    runner resumes with the chosen index (0-based), which we store as
    `selected_restaurant`.

    Reads:  found_restaurants
    Writes: selected_restaurant
    """
    options = state["found_restaurants"]

    choice = interrupt(
        {
            "type": "select_restaurant",
            "prompt": "Pick a restaurant (by number):",
            "options": [
                {
                    "index": i,
                    "name": r["name"],
                    "score": r["score"],
                    "reason": r["reason"],
                    "address": r.get("address", ""),
                    "phone": r.get("phone", ""),
                }
                for i, r in enumerate(options)
            ],
        }
    )

    index = _coerce_index(choice, len(options))
    return {"selected_restaurant": options[index]}


def _coerce_index(choice, count: int) -> int:
    """Normalise a resume value into a valid 0-based option index."""
    if isinstance(choice, dict):
        choice = choice.get("index", choice.get("choice"))
    try:
        index = int(choice)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid choice: {choice!r}")
    if not 0 <= index < count:
        raise ValueError(f"Choice {index} out of range 0..{count - 1}")
    return index


def _coerce_quantity(value) -> int:
    """Normalise a quantity resume value into a positive int (default 1)."""
    if value is None:
        return 1
    try:
        qty = int(value)
    except (TypeError, ValueError):
        return 1
    return qty if qty >= 1 else 1


def find_deals_node(state: ScoutState) -> dict:
    """Node: deep-dive the selected restaurant's menu (Talabat -> Tavily -> estimate).

    Reads:  selected_restaurant, food_entity
    Writes: found_deals (as dicts)
    """
    restaurant = state["selected_restaurant"]
    food_entity = state.get("food_entity", "")

    deals = find_deals(restaurant["name"], food_entity)
    return {"found_deals": [d.model_dump() for d in deals]}


def ask_user_deal(state: ScoutState) -> dict:
    """HITL #2: pause and let the user pick a deal AND set its quantity.

    Calls interrupt() with the deal options. The runner resumes with either:
      - an int index (quantity defaults to 1), or
      - a dict {"index": i, "quantity": q}.

    Reads:  found_deals
    Writes: selected_deal (with the user's chosen quantity)
    """
    options = state["found_deals"]

    choice = interrupt(
        {
            "type": "select_deal",
            "prompt": "Pick a deal (by number) and a quantity:",
            "options": [
                {
                    "index": i,
                    "item_name": d["item_name"],
                    "price": d["price"],
                    "currency": d["currency"],
                    "deal_description": d["deal_description"],
                }
                for i, d in enumerate(options)
            ],
        }
    )

    quantity = 1
    if isinstance(choice, dict):
        quantity = _coerce_quantity(choice.get("quantity"))
    index = _coerce_index(choice, len(options))

    selected = dict(options[index])
    selected["quantity"] = quantity
    return {"selected_deal": selected}


def compile_payload(state: ScoutState) -> dict:
    """Final node: build the strict OrderPayload JSON from the decisions.

    Reads:  food_entity, selected_restaurant, selected_deal
    Writes: payload (the JSON contract for the next agent)
    """
    payload = build_payload(
        user_intent=state.get("food_entity", ""),
        selected_restaurant=state["selected_restaurant"],
        selected_deal=state["selected_deal"],
    )
    return {"payload": payload.model_dump()}
