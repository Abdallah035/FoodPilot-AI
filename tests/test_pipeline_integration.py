from langgraph.types import Command

from agent1_scout import nodes
from agent1_scout.graph import build_graph
from agent1_scout.intent import Intent
from agent1_scout.state import Coordinates, Deal, Restaurant
from pipeline import enrich_payload_with_rag, run_post_scout_pipeline


class FakeFinalizerApp:
    def __init__(self):
        self.received_state = None

    def invoke(self, state):
        self.received_state = state
        payload = state["payload"]
        deal = payload["selected_deal"]
        return {
            **state,
            "verified_promo": None,
            "final_price": float(deal["price"]) * deal["quantity"],
            "receipt_summary": f"Receipt for {deal['quantity']}x {deal['item_name']}",
        }


def _restaurants():
    return [
        Restaurant(name="Koshary House", coordinates=Coordinates(lat=29.961, lon=31.261), rating=4.6, reviews=2000),
        Restaurant(name="Burger House", coordinates=Coordinates(lat=29.965, lon=31.265), rating=4.4, reviews=500),
    ]


def _fake_rag_calculator(order, vectorstore, llm, all_dishes, json_path):
    assert order == [{"name": "koshary", "quantity": "1 Large serving(s)", "context": "koshary | large bowl | Large"}]
    assert json_path.endswith("data.json")
    return [{
        "name": "koshary",
        "quantity": order[0]["quantity"],
        "quantity_grams": 450.0,
        "calories_per_100g": 150.0,
        "calories_per_meal": 675.0,
        "found": True,
        "source": "rag",
    }]


def _fake_partial_rag_calculator(order, vectorstore, llm, all_dishes, json_path):
    return [{
        "name": order[0]["name"],
        "quantity": order[0]["quantity"],
        "quantity_grams": 200.0,
        "calories_per_100g": None,
        "calories_per_meal": None,
        "found": False,
        "source": None,
    }]


def _fake_failing_rag_calculator(order, vectorstore, llm, all_dishes, json_path):
    raise RuntimeError("RAG offline")


def _run_scout_payload(monkeypatch):
    monkeypatch.setattr(nodes, "parse_intent", lambda q: Intent(food_entity="koshary", budget=None))
    monkeypatch.setattr(nodes, "search_restaurants", lambda food, loc, n=5: _restaurants())
    monkeypatch.setattr(
        nodes,
        "find_deals",
        lambda name, food: [
            Deal(item_name="Koshari Box", price="80", deal_description="large bowl", portion="Large"),
        ],
    )

    app = build_graph()
    cfg = {"configurable": {"thread_id": "integrated-1"}}
    app.invoke({
        "user_query": "عايز كشري",
        "location_query": "Tahrir, Cairo",
        "user_coords": {"lat": 29.9600, "lon": 31.2600},
    }, cfg)
    app.invoke(Command(resume=0), cfg)
    final = app.invoke(Command(resume={"index": 0, "quantity": 2}), cfg)
    return final["payload"]


def test_rag_enrichment_preserves_scout_payload_and_adds_sources():
    payload = {
        "order_status": "configured",
        "user_intent": "koshary",
        "selected_restaurant": {"name": "Koshary House"},
        "selected_deal": {"item_name": "Koshari Box", "deal_description": "large bowl", "portion": "Large"},
    }

    enriched = enrich_payload_with_rag(
        payload,
        rag_dependencies=(object(), object(), []),
        rag_calculator=_fake_rag_calculator,
    )

    assert enriched["payload"] is payload
    assert enriched["rag_enrichment"]["status"] == "completed"
    assert enriched["rag_enrichment"]["sources"] == ["koshary (rag)"]
    assert enriched["rag_enrichment"]["items"][0]["calories_per_meal"] == 675.0
    assert "approximately 675 calories" in enriched["rag_enrichment"]["answer"]


def test_rag_skipped_preserves_payload_and_marks_skipped():
    payload = {
        "order_status": "configured",
        "selected_deal": {"item_name": "Burger", "quantity": 1},
    }

    enriched = enrich_payload_with_rag(payload, enabled=False)

    assert enriched["payload"] is payload
    assert enriched["rag_enrichment"] == {
        "status": "skipped",
        "answer": "",
        "sources": [],
        "items": [],
    }


def test_rag_partial_when_dish_not_found():
    payload = {
        "order_status": "configured",
        "selected_deal": {"item_name": "Unknown Dish", "quantity": 2},
    }

    enriched = enrich_payload_with_rag(
        payload,
        rag_dependencies=(object(), object(), []),
        rag_calculator=_fake_partial_rag_calculator,
    )

    assert enriched["rag_enrichment"]["status"] == "partial"
    assert enriched["rag_enrichment"]["items"][0]["found"] is False
    assert "calorie data was not found" in enriched["rag_enrichment"]["answer"]


def test_rag_exception_returns_failed_without_changing_payload():
    payload = {
        "order_status": "configured",
        "selected_deal": {"item_name": "Koshari Box", "quantity": 1},
    }

    enriched = enrich_payload_with_rag(
        payload,
        rag_dependencies=(object(), object(), []),
        rag_calculator=_fake_failing_rag_calculator,
    )

    assert enriched["payload"] is payload
    assert enriched["rag_enrichment"]["status"] == "failed"
    assert enriched["rag_enrichment"]["items"] == []
    assert "RAG offline" in enriched["rag_enrichment"]["error"]


def test_full_module_handoff_scout_to_rag_to_finalizer(monkeypatch):
    scout_payload = _run_scout_payload(monkeypatch)
    finalizer = FakeFinalizerApp()

    result = run_post_scout_pipeline(
        scout_payload,
        rag_dependencies=(object(), object(), []),
        rag_calculator=lambda order, vectorstore, llm, all_dishes, json_path: [{
            "name": order[0]["name"],
            "quantity": order[0]["quantity"],
            "quantity_grams": 900.0,
            "calories_per_100g": 150.0,
            "calories_per_meal": 1350.0,
            "found": True,
            "source": "rag",
        }],
        finalizer_app=finalizer,
    )

    assert finalizer.received_state["payload"] == scout_payload
    assert finalizer.received_state["rag_enrichment"]["status"] == "completed"
    assert finalizer.received_state["rag_enrichment"]["sources"] == ["koshary (rag)"]
    assert result["payload"]["selected_deal"]["quantity"] == 2
    assert result["final_price"] == 160.0
    assert result["receipt_summary"] == "Receipt for 2x Koshari Box"


def test_finalizer_runs_when_rag_fails():
    payload = {
        "order_status": "configured",
        "selected_restaurant": {"name": "Koshary House"},
        "selected_deal": {"item_name": "Koshari Box", "price": "80", "quantity": 2},
    }
    finalizer = FakeFinalizerApp()

    result = run_post_scout_pipeline(
        payload,
        rag_dependencies=(object(), object(), []),
        rag_calculator=_fake_failing_rag_calculator,
        finalizer_app=finalizer,
    )

    assert result["rag_enrichment"]["status"] == "failed"
    assert finalizer.received_state["rag_enrichment"]["status"] == "failed"
    assert result["final_price"] == 160.0
