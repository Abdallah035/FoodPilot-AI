"""Task 9 — tests for find_deals node + HITL #2 (pick deal + quantity)."""

import pytest

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from agent1_scout import nodes
from agent1_scout.nodes import (
    _coerce_quantity,
    ask_user_deal,
    find_deals_node,
)
from agent1_scout.state import Deal, ScoutState

DEALS = [
    {"item_name": "Chicken Ranch Pizza", "price": "160", "currency": "EGP", "deal_description": "medium"},
    {"item_name": "Margherita Pizza", "price": "120", "currency": "EGP", "deal_description": ""},
    {"item_name": "Pepperoni Pizza", "price": "150", "currency": "EGP", "deal_description": "large"},
]


# --- quantity coercion -------------------------------------------------------
def test_coerce_quantity_defaults_and_bounds():
    assert _coerce_quantity(None) == 1
    assert _coerce_quantity("3") == 3
    assert _coerce_quantity(0) == 1     # min 1
    assert _coerce_quantity(-5) == 1
    assert _coerce_quantity("abc") == 1


# --- find_deals node wiring --------------------------------------------------
def test_find_deals_node(monkeypatch):
    monkeypatch.setattr(
        nodes, "find_deals",
        lambda name, food: [Deal(item_name="Pizza", price="120")],
    )
    state = {"selected_restaurant": {"name": "Primo's Pizza"}, "food_entity": "pizza"}
    out = find_deals_node(state)
    assert len(out["found_deals"]) == 1
    assert out["found_deals"][0]["item_name"] == "Pizza"


# --- interrupt #2 pause/resume with quantity --------------------------------
def _tiny_graph():
    g = StateGraph(ScoutState)
    g.add_node("ask_user_deal", ask_user_deal)
    g.add_edge(START, "ask_user_deal")
    g.add_edge("ask_user_deal", END)
    return g.compile(checkpointer=MemorySaver())


def test_graph_pauses_then_resumes_with_deal_and_quantity():
    app = _tiny_graph()
    cfg = {"configurable": {"thread_id": "d1"}}

    result = app.invoke({"found_deals": DEALS}, cfg)
    assert "__interrupt__" in result  # paused at HITL #2
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "select_deal"
    assert len(payload["options"]) == 3

    # user picks option 0 with quantity 2
    final = app.invoke(Command(resume={"index": 0, "quantity": 2}), cfg)
    chosen = final["selected_deal"]
    assert chosen["item_name"] == "Chicken Ranch Pizza"
    assert chosen["quantity"] == 2


def test_resume_with_plain_index_defaults_quantity_1():
    app = _tiny_graph()
    cfg = {"configurable": {"thread_id": "d2"}}
    app.invoke({"found_deals": DEALS}, cfg)
    final = app.invoke(Command(resume=2), cfg)  # just an index
    assert final["selected_deal"]["item_name"] == "Pepperoni Pizza"
    assert final["selected_deal"]["quantity"] == 1
