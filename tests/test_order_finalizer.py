from langchain_core.runnables import RunnableLambda

from order_finalizer import graph as finalizer_graph
from order_finalizer import nodes as finalizer_nodes


def _state(price="120", quantity=2, promo=None):
    state = {
        "payload": {
            "selected_restaurant": {"name": "Koshary House", "phone": "01000000000"},
            "selected_deal": {
                "item_name": "Koshari Box",
                "price": price,
                "quantity": quantity,
            },
        },
    }
    if promo is not None:
        state["verified_promo"] = promo
    return state


def test_calculate_price_node_multiplies_quantity():
    result = finalizer_nodes.calculate_price_node(_state(price="120 EGP", quantity=3))

    assert result["final_price"] == 360.0


def test_calculate_price_node_percentage_promo():
    result = finalizer_nodes.calculate_price_node(
        _state(
            price="100",
            quantity=2,
            promo={"code": "SAVE10", "discount_type": "percentage", "value": 10.0, "required_platform": "Talabat"},
        )
    )

    assert result["final_price"] == 180.0


def test_calculate_price_node_flat_promo_does_not_go_negative():
    result = finalizer_nodes.calculate_price_node(
        _state(
            price="50",
            quantity=1,
            promo={"code": "SAVE100", "discount_type": "flat", "value": 100.0, "required_platform": "Talabat"},
        )
    )

    assert result["final_price"] == 0.0


def test_calculate_price_node_invalid_and_zero_price():
    assert finalizer_nodes.calculate_price_node(_state(price="free", quantity=2))["final_price"] == 0.0
    assert finalizer_nodes.calculate_price_node(_state(price="0 EGP", quantity=2))["final_price"] == 0.0


def test_calculate_price_node_comma_formatted_price():
    result = finalizer_nodes.calculate_price_node(_state(price="1,200 EGP", quantity=2))

    assert result["final_price"] == 2400.0


def test_verify_promo_node_extracts_json(monkeypatch):
    fake_llm = RunnableLambda(lambda _: '```json\n{"code":"FOOD20","discount_type":"percentage","value":20,"required_platform":"Talabat"}\n```')
    monkeypatch.setattr(finalizer_nodes, "get_llm", lambda: fake_llm)

    result = finalizer_nodes.verify_promo_node({**_state(), "raw_search_results": "FOOD20 for Koshary House"})

    assert result["verified_promo"] == {
        "code": "FOOD20",
        "discount_type": "percentage",
        "value": 20,
        "required_platform": "Talabat",
    }


def test_verify_promo_node_returns_none_for_empty_json(monkeypatch):
    monkeypatch.setattr(finalizer_nodes, "get_llm", lambda: RunnableLambda(lambda _: "{}"))

    result = finalizer_nodes.verify_promo_node({**_state(), "raw_search_results": "no useful promo"})

    assert result["verified_promo"] is None


def test_generate_receipt_node_includes_rag_context(monkeypatch):
    nutrition = "Koshari Box: approximately 675 calories."
    phone = "01000000000"

    def fake_receipt(prompt_value):
        prompt = prompt_value.to_string()
        assert nutrition in prompt
        assert f"Phone: {phone}" in prompt
        assert "Contact info will be provided" not in prompt
        return "Receipt with nutrition"

    monkeypatch.setattr(finalizer_nodes, "get_llm", lambda: RunnableLambda(fake_receipt))

    result = finalizer_nodes.generate_receipt_node({
        **_state(),
        "verified_promo": None,
        "final_price": 240.0,
        "rag_enrichment": {"answer": nutrition},
    })

    assert result["receipt_summary"] == "Receipt with nutrition"


def test_finalizer_graph_with_mocked_external_nodes(monkeypatch):
    monkeypatch.setattr(finalizer_nodes, "search_promos", lambda restaurant: "SAVE10 for Koshary House")
    monkeypatch.setattr(finalizer_graph, "search_promos_node", finalizer_nodes.search_promos_node)
    monkeypatch.setattr(finalizer_nodes, "get_llm", lambda: RunnableLambda(lambda _: "{}"))
    monkeypatch.setattr(finalizer_graph, "verify_promo_node", finalizer_nodes.verify_promo_node)
    monkeypatch.setattr(finalizer_graph, "generate_receipt_node", lambda state: {"receipt_summary": "Final receipt"})

    app = finalizer_graph.build_graph()
    result = app.invoke(_state(price="80", quantity=2))

    assert result["final_price"] == 160.0
    assert result["receipt_summary"] == "Final receipt"
