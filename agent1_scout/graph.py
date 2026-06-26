"""Task 11 — Assemble the Scout LangGraph.

Flow:
    START
      -> find_restaurants        (Apify + scoring -> top 3)
      -> ask_user_restaurant     (INTERRUPT #1: pick a restaurant)
      -> find_deals_node         (Talabat -> Tavily -> estimate)
      -> ask_user_deal           (INTERRUPT #2: pick a deal + quantity)
      -> compile_payload         (build the JSON payload)
    END
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes import (
    ask_user_deal,
    ask_user_restaurant,
    compile_payload,
    find_deals_node,
    find_restaurants,
)
from .state import ScoutState


def build_graph(checkpointer=None):
    """Build and compile the Scout graph.

    A checkpointer is REQUIRED for the interrupts to pause/resume. Defaults to
    an in-memory saver; pass a persistent one for production.
    """
    g = StateGraph(ScoutState)

    g.add_node("find_restaurants", find_restaurants)
    g.add_node("ask_user_restaurant", ask_user_restaurant)
    g.add_node("find_deals_node", find_deals_node)
    g.add_node("ask_user_deal", ask_user_deal)
    g.add_node("compile_payload", compile_payload)

    g.add_edge(START, "find_restaurants")
    g.add_edge("find_restaurants", "ask_user_restaurant")
    g.add_edge("ask_user_restaurant", "find_deals_node")
    g.add_edge("find_deals_node", "ask_user_deal")
    g.add_edge("ask_user_deal", "compile_payload")
    g.add_edge("compile_payload", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())
