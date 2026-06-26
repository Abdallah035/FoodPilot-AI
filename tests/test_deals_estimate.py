"""Task 8c — tests for LLM price estimation of missing prices."""

import pytest

import config
from agent1_scout.deals_estimate import (
    ESTIMATE_NOTE,
    _needs_price,
    estimate_missing_prices,
)
from agent1_scout.state import Deal


def test_needs_price():
    assert _needs_price(Deal(item_name="x", price=""))
    assert _needs_price(Deal(item_name="x", price="0"))
    assert not _needs_price(Deal(item_name="x", price="50"))


def test_real_prices_untouched(monkeypatch):
    # if nothing needs a price, no LLM is called and deals are unchanged
    deals = [Deal(item_name="Pizza", price="120"), Deal(item_name="Cola", price="25")]
    out = estimate_missing_prices(deals, "Some Place")
    assert [d.price for d in out] == ["120", "25"]
    assert all(ESTIMATE_NOTE not in d.deal_description for d in out)


def test_missing_price_gets_flagged_estimate(monkeypatch):
    class FakeMessage:
        content = "EGP 95"  # model may add words; we strip them

    class FakeLLM:
        def __init__(self, *a, **k):
            pass

        def invoke(self, prompt):
            return FakeMessage()

    monkeypatch.setattr(config, "get_azure_openai_llm", lambda temperature=0.0: FakeLLM())

    deals = [
        Deal(item_name="Shawarma Sandwich", price="", deal_description="beef"),
        Deal(item_name="Fries", price="30"),
    ]
    out = estimate_missing_prices(deals, "Test Grill")

    shawarma = next(d for d in out if d.item_name == "Shawarma Sandwich")
    fries = next(d for d in out if d.item_name == "Fries")

    assert shawarma.price == "95"  # digits only
    assert ESTIMATE_NOTE in shawarma.deal_description
    assert "beef" in shawarma.deal_description  # original desc preserved
    # the real-priced item is untouched
    assert fries.price == "30"
    assert ESTIMATE_NOTE not in fries.deal_description


@pytest.mark.skipif(not config.RUN_AZURE_EST, reason="set RUN_AZURE_EST=1 for live estimate")
def test_estimate_live():
    out = estimate_missing_prices([Deal(item_name="Koshary medium", price="")], "Koshary El Tahrir")
    assert out[0].price.isdigit()
    assert ESTIMATE_NOTE in out[0].deal_description
