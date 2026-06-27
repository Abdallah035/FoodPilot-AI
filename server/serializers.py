"""Translate backend domain objects into the frontend event/JSON shapes.

These mirror `web/src/lib/types.ts`. Keep both in sync.
"""

from __future__ import annotations

import re
from typing import Any


def _slug(value: str, fallback: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return base or fallback


def restaurant_to_json(raw: dict[str, Any], index: int) -> dict[str, Any]:
    """Map a Scout `Restaurant` (dict form in state) to the UI Restaurant shape."""
    coords = raw.get("coordinates") or {}
    return {
        "id": f"r{index}_{_slug(raw.get('name', ''), str(index))}",
        "name": raw.get("name", "Unknown"),
        "address": raw.get("address") or "",
        "phone": raw.get("phone") or "",
        "coordinates": {
            "lat": coords.get("lat"),
            "lon": coords.get("lon"),
        }
        if coords
        else None,
        "rating": raw.get("rating", 0.0) or 0.0,
        "reviews": raw.get("reviews", 0) or 0,
        "price_level": raw.get("price_level"),
        "distance_km": raw.get("distance_km"),
        "score": raw.get("score"),
        "reason": raw.get("reason"),
        "cuisine": raw.get("cuisine") or "",
        "image": raw.get("image"),
        # Apify does not always return opening hours; default to open.
        "open": raw.get("open", True),
    }


def deal_to_json(raw: dict[str, Any], index: int) -> dict[str, Any]:
    """Map a Scout `Deal` (dict form) to the UI Deal shape."""
    return {
        "id": f"d{index}_{_slug(raw.get('item_name', ''), str(index))}",
        "item_name": raw.get("item_name", "Item"),
        "price": raw.get("price", ""),
        "currency": raw.get("currency", "EGP"),
        "deal_description": raw.get("deal_description", ""),
        "source_url": raw.get("source_url", ""),
        "quantity": raw.get("quantity", 1),
        "portion": raw.get("portion", ""),
        "discount": raw.get("discount"),
        "image": raw.get("image"),
        "calories": raw.get("calories"),
        "ingredients": raw.get("ingredients"),
    }


def interrupt_to_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Map a LangGraph interrupt payload (see main.py `_print_interrupt`) to an
    `AgentEvent` of type `interrupt`."""
    kind = payload.get("type")
    prompt = payload.get("prompt", "")

    if kind == "select_restaurant":
        return {
            "type": "interrupt",
            "interrupt": {
                "type": "select_restaurant",
                "prompt": prompt,
                "options": [restaurant_to_json(opt, i) for i, opt in enumerate(payload["options"])],
            },
        }

    if kind == "select_deal":
        return {
            "type": "interrupt",
            "interrupt": {
                "type": "select_deal",
                "prompt": prompt,
                "options": [deal_to_json(opt, i) for i, opt in enumerate(payload["options"])],
            },
        }

    # no_deals
    return {
        "type": "interrupt",
        "interrupt": {
            "type": "no_deals",
            "prompt": prompt,
            "restaurant": restaurant_to_json(payload.get("restaurant", {}), 0),
            "options": [
                {"index": opt["index"], "label": opt["label"]} for opt in payload.get("options", [])
            ],
        },
    }


def nutrition_event(
    rag_enrichment: dict[str, Any],
    meal: str,
    ingredients: list[str] | None = None,
) -> dict[str, Any] | None:
    """Build a `nutrition` AgentEvent from the RAG enrichment block.

    The RAG agent returns CALORIES ONLY (see RAG/Rag.py calculate_order_calories):
    { name, quantity, quantity_grams, calories_per_100g, calories_per_meal,
      found, source }. We surface exactly that, plus ingredients (from the RAG
      dish data, passed in by the caller). No macros are invented.
    """
    items = rag_enrichment.get("items") or []
    if not items:
        return None

    first = items[0]
    nutrition = {
        "calories_per_meal": first.get("calories_per_meal"),
        "calories_per_100g": _calories_number(first.get("calories_per_100g")),
        "quantity_grams": first.get("quantity_grams"),
        "ingredients": ingredients or first.get("ingredients") or [],
        "found": bool(first.get("found")),
        "source": first.get("source"),
    }
    return {"type": "nutrition", "nutrition": nutrition, "meal": meal}


def _calories_number(value: Any) -> float | None:
    """calories_per_100g may be a number or a string like '140 سعرة لكل 100 غرام'."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None


def order_event(pipeline_result: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Build an `order` AgentEvent from the real finalizer result.

    Uses only values the Order agent produces: verified_promo, final_price (after
    promo × quantity), receipt_summary. Includes the restaurant phone so the user
    can CALL to place the order.
    """
    deal = payload.get("selected_deal", {})
    restaurant = payload.get("selected_restaurant", {})

    def _num(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(re.sub(r"[^\d.]", "", str(value or "0")) or 0)
        except ValueError:
            return 0.0

    quantity = int(deal.get("quantity", 1) or 1)
    unit_price = _num(deal.get("price"))
    subtotal = unit_price * quantity

    final_price = pipeline_result.get("final_price")
    total = _num(final_price) if final_price is not None else subtotal
    promo = pipeline_result.get("verified_promo")
    discount = max(0.0, subtotal - total)

    return {
        "type": "order",
        "order": {
            "restaurant": restaurant.get("name", ""),
            "phone": restaurant.get("phone", ""),
            "address": restaurant.get("address", ""),
            "meal": deal.get("item_name", ""),
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "promo": promo,
            "subtotal": round(subtotal, 2),
            "discount": round(discount, 2),
            "total": round(total, 2),
            "currency": deal.get("currency", "EGP"),
            "savings": round(discount, 2),
            "receipt": pipeline_result.get("receipt_summary", ""),
        },
    }
