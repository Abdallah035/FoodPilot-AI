"""Task 11 — full graph wiring test (all external calls mocked).

Verifies the graph runs find_restaurants -> HITL#1 -> find_deals -> HITL#2 ->
compile_payload, pausing at each interrupt and producing the correct payload.
"""

from langgraph.types import Command

from agent1_scout import nodes
from agent1_scout.graph import build_graph
from agent1_scout.intent import Intent
from agent1_scout.state import Coordinates, Deal, Restaurant


def _restaurants():
    return [
        Restaurant(name="Burger House", coordinates=Coordinates(lat=29.961, lon=31.261), rating=4.6, reviews=2000),
        Restaurant(name="Smash Bros", coordinates=Coordinates(lat=29.965, lon=31.265), rating=4.4, reviews=500),
        Restaurant(name="Far Grill", coordinates=Coordinates(lat=30.10, lon=31.40), rating=5.0, reviews=3),
    ]


def test_full_graph_end_to_end(monkeypatch):
    # mock intent, Apify discovery, and deal lookup
    monkeypatch.setattr(nodes, "parse_intent", lambda q: Intent(food_entity="burger", budget=None))
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: _restaurants())
    monkeypatch.setattr(
        nodes, "find_deals",
        lambda name, food: [
            Deal(item_name="Double Burger", price="180", deal_description="combo"),
            Deal(item_name="Single Burger", price="120"),
        ],
    )

    app = build_graph()
    cfg = {"configurable": {"thread_id": "full-1"}}

    state = {
        "user_query": "I'm craving a good burger",
        "location_query": "Maadi, Cairo",
        "user_coords": {"lat": 29.9600, "lon": 31.2600},
    }

    # run -> pause at HITL #1
    r1 = app.invoke(state, cfg)
    p1 = r1["__interrupt__"][0].value
    assert p1["type"] == "select_restaurant"
    assert len(p1["options"]) == 3
    assert p1["options"][0]["name"] == "Burger House"  # near + well reviewed ranks first

    # pick restaurant 0 -> pause at HITL #2
    r2 = app.invoke(Command(resume=0), cfg)
    p2 = r2["__interrupt__"][0].value
    assert p2["type"] == "select_deal"
    assert len(p2["options"]) == 2

    # pick deal 0 with quantity 3 -> finish
    r3 = app.invoke(Command(resume={"index": 0, "quantity": 3}), cfg)
    payload = r3["payload"]

    assert payload["order_status"] == "configured"
    assert payload["user_intent"] == "burger"
    assert payload["selected_restaurant"]["name"] == "Burger House"
    assert payload["selected_deal"]["item_name"] == "Double Burger"
    assert payload["selected_deal"]["quantity"] == 3
    # exact spec keys
    assert set(payload.keys()) == {"order_status", "user_intent", "selected_restaurant", "selected_deal"}


def test_graph_no_deals_can_return_restaurant_info(monkeypatch):
    monkeypatch.setattr(nodes, "parse_intent", lambda q: Intent(food_entity="burger", budget=None))
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: _restaurants())
    monkeypatch.setattr(nodes, "find_deals", lambda name, food: [])

    app = build_graph()
    cfg = {"configurable": {"thread_id": "no-deals-full-1"}}
    state = {
        "user_query": "I'm craving a good burger",
        "location_query": "Maadi, Cairo",
        "user_coords": {"lat": 29.9600, "lon": 31.2600},
    }

    app.invoke(state, cfg)
    result = app.invoke(Command(resume=0), cfg)
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "no_deals"

    final = app.invoke(Command(resume=0), cfg)
    assert final["no_deals_action"] == "show_info"
    assert "payload" not in final


def test_graph_no_deals_can_choose_another_restaurant(monkeypatch):
    calls = []

    def fake_find_deals(name, food):
        calls.append(name)
        if name == "Burger House":
            return []
        return [Deal(item_name="Single Burger", price="120")]

    monkeypatch.setattr(nodes, "parse_intent", lambda q: Intent(food_entity="burger", budget=None))
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: _restaurants())
    monkeypatch.setattr(nodes, "find_deals", fake_find_deals)

    app = build_graph()
    cfg = {"configurable": {"thread_id": "no-deals-full-2"}}
    state = {
        "user_query": "I'm craving a good burger",
        "location_query": "Maadi, Cairo",
        "user_coords": {"lat": 29.9600, "lon": 31.2600},
    }

    app.invoke(state, cfg)
    app.invoke(Command(resume=0), cfg)
    result = app.invoke(Command(resume=1), cfg)
    assert result["__interrupt__"][0].value["type"] == "select_restaurant"

    result = app.invoke(Command(resume=1), cfg)
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "select_deal"
    assert calls == ["Burger House", "Smash Bros"]
