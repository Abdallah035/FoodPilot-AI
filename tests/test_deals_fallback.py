"""Task 8b — tests for the Tavily open-web fallback."""

import pytest

import config
from agent1_scout.deals_fallback import (
    DealList,
    _extract_deals,
    tavily_menu_fallback,
)
from agent1_scout.state import Deal


def test_extract_deals_empty_results():
    # no web results -> no deals (and no LLM call needed)
    assert _extract_deals([], "Some Place", "burger") == []


def test_extract_deals_uses_llm(monkeypatch):
    """_extract_deals feeds snippets to the LLM and returns its deals."""
    captured = {}

    class FakeStructured:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return DealList(deals=[Deal(item_name="Koshary Large", price="45")])

    class FakeLLM:
        def __init__(self, *a, **k):
            pass

        def with_structured_output(self, schema):
            return FakeStructured()

    monkeypatch.setattr(config, "get_azure_openai_llm", lambda temperature=0.0: FakeLLM())

    results = [{"url": "http://e.com", "title": "Menu", "content": "Koshary 45 EGP"}]
    deals = _extract_deals(results, "Koshary El Tahrir", "koshary")
    assert len(deals) == 1
    assert deals[0].item_name == "Koshary Large"
    # the restaurant + snippet made it into the prompt
    assert "Koshary El Tahrir" in captured["prompt"]
    assert "45 EGP" in captured["prompt"]


@pytest.mark.skipif(not config.RUN_TAVILY, reason="set RUN_TAVILY=1 to hit Tavily+Azure OpenAI")
def test_tavily_menu_fallback_live():
    deals = tavily_menu_fallback("Koshary El Tahrir", "koshary")
    assert isinstance(deals, list)
    for d in deals:
        assert isinstance(d, Deal)
        assert d.item_name
