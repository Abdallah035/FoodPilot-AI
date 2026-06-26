"""Task 12 — LangSmith tracing checks.

Offline test verifies the tracing config flag. A gated live test runs the
(mocked-tools) graph under @traceable and confirms a run reaches LangSmith.
"""

import pytest

import config


def test_tracing_config_flag():
    assert isinstance(config.tracing_enabled(), bool)
    if config.LANGSMITH_TRACING and not config.LANGSMITH_API_KEY:
        assert config.tracing_enabled() is False


@pytest.mark.skipif(
    not config.RUN_TRACE or not config.tracing_enabled(),
    reason="set RUN_TRACE=1 with LangSmith configured",
)
def test_graph_run_is_traced(monkeypatch):
    """Run the graph end-to-end (mocked tools) and confirm a trace is sent."""
    from langsmith import Client

    from agent1_scout import nodes
    from agent1_scout.graph import build_graph
    from agent1_scout.intent import Intent
    from agent1_scout.state import Coordinates, Deal, Restaurant
    from langgraph.types import Command

    monkeypatch.setattr(nodes, "parse_intent", lambda q: Intent(food_entity="burger", budget=None))
    monkeypatch.setattr(
        nodes, "search_restaurants",
        lambda food, loc, n=5: [Restaurant(name="Burger House", coordinates=Coordinates(lat=29.961, lon=31.261), rating=4.6, reviews=2000)],
    )
    monkeypatch.setattr(nodes, "find_deals", lambda name, food: [Deal(item_name="Burger", price="120")])

    app = build_graph()
    cfg = {"configurable": {"thread_id": "trace-1"}}
    app.invoke({"user_query": "burger", "location_query": "Maadi", "user_coords": {"lat": 29.96, "lon": 31.26}}, cfg)
    app.invoke(Command(resume=0), cfg)
    app.invoke(Command(resume={"index": 0, "quantity": 1}), cfg)

    # the run should now exist in the project
    client = Client()
    runs = list(client.list_runs(project_name=config.LANGSMITH_PROJECT, limit=1))
    assert runs, "no runs found in LangSmith project"
