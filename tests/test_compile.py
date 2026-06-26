"""Task 10 — tests for building the JSON output payload."""

from agent1_scout.compile import build_payload
from agent1_scout.nodes import compile_payload
from agent1_scout.state import OrderPayload

SELECTED_RESTAURANT = {
    "name": "Primo's Pizza - Maadi",
    "address": "Road 9, Maadi, Cairo",
    "phone": "+20 2 12345678",
    "coordinates": {"lat": 29.9601, "lon": 31.2569},
    "rating": 4.6,
    "reviews": 342,
    "price_level": "E£200–400",
    "distance_km": 0.8,
    "score": 0.77,
    "reason": "4.6★ (342 reviews), 0.8 km away, $$",
}

SELECTED_DEAL = {
    "item_name": "Chicken Ranch Pizza",
    "price": "160",
    "currency": "EGP",
    "deal_description": "medium",
    "source_url": "https://www.talabat.com/egypt/primos-pizza",
    "quantity": 2,
    "portion": "",
}


def test_build_payload_shape():
    payload = build_payload("pizza", SELECTED_RESTAURANT, SELECTED_DEAL)
    assert isinstance(payload, OrderPayload)
    dumped = payload.model_dump()

    # exact top-level keys per spec §5
    assert set(dumped.keys()) == {
        "order_status", "user_intent", "selected_restaurant", "selected_deal",
    }
    assert dumped["order_status"] == "configured"
    assert dumped["user_intent"] == "pizza"

    sr = dumped["selected_restaurant"]
    assert set(sr.keys()) == {"name", "address", "phone", "coordinates", "google_maps_rating"}
    assert sr["coordinates"] == {"lat": 29.9601, "lon": 31.2569}
    assert sr["phone"] == "+20 2 12345678"
    assert sr["google_maps_rating"] == 4.6
    # scoring-only fields must NOT leak into the payload
    assert "score" not in sr and "distance_km" not in sr

    sd = dumped["selected_deal"]
    assert sd["item_name"] == "Chicken Ranch Pizza"
    assert sd["price"] == "160"
    assert sd["quantity"] == 2  # the user's chosen quantity carried through


def test_compile_payload_node():
    state = {
        "food_entity": "pizza",
        "selected_restaurant": SELECTED_RESTAURANT,
        "selected_deal": SELECTED_DEAL,
    }
    out = compile_payload(state)
    assert "payload" in out
    assert out["payload"]["user_intent"] == "pizza"
    assert out["payload"]["selected_deal"]["quantity"] == 2


def test_payload_arabic_intent():
    deal = dict(SELECTED_DEAL, item_name="بيتزا فراخ رانش")
    payload = build_payload("بيتزا", SELECTED_RESTAURANT, deal)
    dumped = payload.model_dump()
    assert dumped["user_intent"] == "بيتزا"
    assert dumped["selected_deal"]["item_name"] == "بيتزا فراخ رانش"
