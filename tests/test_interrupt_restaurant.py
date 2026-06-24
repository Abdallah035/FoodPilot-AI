"""Task 7 — tests for HITL #1 (pick restaurant) interrupt."""

import pytest

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from agent1_scout.nodes import _coerce_index, ask_user_restaurant
from agent1_scout.state import ScoutState

OPTIONS = [
    {"name": "الشبراوي", "score": 0.81, "reason": "4.3★ (5200), 0.2 km", "distance_km": 0.2},
    {"name": "كفتة ستيشن", "score": 0.74, "reason": "4.5★ (760), 0.6 km", "distance_km": 0.6},
    {"name": "جراند كفتة", "score": 0.41, "reason": "4.9★ (30), 12 km", "distance_km": 12.0},
]


# --- index coercion ----------------------------------------------------------
def test_coerce_index_int():
    assert _coerce_index(0, 3) == 0
    assert _coerce_index("2", 3) == 2


def test_coerce_index_dict():
    assert _coerce_index({"index": 1}, 3) == 1
    assert _coerce_index({"choice": 2}, 3) == 2


def test_coerce_index_out_of_range():
    with pytest.raises(ValueError):
        _coerce_index(5, 3)


def test_coerce_index_garbage():
    with pytest.raises(ValueError):
        _coerce_index("abc", 3)


# --- interrupt + resume in a real graph -------------------------------------
def _tiny_graph():
    g = StateGraph(ScoutState)
    g.add_node("ask_user_restaurant", ask_user_restaurant)
    g.add_edge(START, "ask_user_restaurant")
    g.add_edge("ask_user_restaurant", END)
    return g.compile(checkpointer=MemorySaver())


def test_graph_pauses_then_resumes_with_choice():
    app = _tiny_graph()
    cfg = {"configurable": {"thread_id": "t1"}}

    # run until the interrupt
    result = app.invoke({"found_restaurants": OPTIONS}, cfg)
    assert "__interrupt__" in result  # graph paused at HITL #1
    payload = result["__interrupt__"][0].value
    assert payload["type"] == "select_restaurant"
    assert len(payload["options"]) == 3

    # resume by choosing option index 1
    final = app.invoke(Command(resume=1), cfg)
    assert final["selected_restaurant"]["name"] == "كفتة ستيشن"
