"""Task 8d — tests for the find_deals orchestrator (Talabat -> Tavily -> estimate)."""

import pytest

import config
from agent1_scout import deals as deals_mod
from agent1_scout.deals import find_deals
from agent1_scout.state import Deal


def test_uses_talabat_when_available(monkeypatch):
    talabat_called = {"n": 0}
    fallback_called = {"n": 0}

    def fake_talabat(name, food, country="eg"):
        talabat_called["n"] += 1
        return [Deal(item_name="Pizza", price="120")]

    def fake_fallback(name, food=""):
        fallback_called["n"] += 1
        return []

    monkeypatch.setattr(deals_mod, "talabat_menu", fake_talabat)
    monkeypatch.setattr("agent1_scout.deals_fallback.tavily_menu_fallback", fake_fallback)
    # estimate is a no-op here (price present)
    monkeypatch.setattr(
        "agent1_scout.deals_estimate.estimate_missing_prices", lambda d, n: d
    )

    out = find_deals("Primo's Pizza", "pizza")
    assert [d.item_name for d in out] == ["Pizza"]
    assert talabat_called["n"] == 1
    assert fallback_called["n"] == 0  # talabat had results -> no fallback


def test_falls_back_to_tavily_when_talabat_empty(monkeypatch):
    monkeypatch.setattr(deals_mod, "talabat_menu", lambda n, f, country="eg": [])
    monkeypatch.setattr(
        "agent1_scout.deals_fallback.tavily_menu_fallback",
        lambda n, f="": [Deal(item_name="Koshary", price="")],
    )
    # estimate fills the missing price + flags it
    monkeypatch.setattr(
        "agent1_scout.deals_estimate.estimate_missing_prices",
        lambda deals, name: [d.model_copy(update={"price": "40", "deal_description": "(estimated price)"}) for d in deals],
    )

    out = find_deals("Tiny Local Spot", "koshary")
    assert out[0].item_name == "Koshary"
    assert out[0].price == "40"
    assert "estimated" in out[0].deal_description


def test_limit_applied(monkeypatch):
    many = [Deal(item_name=f"Item {i}", price="10") for i in range(50)]
    monkeypatch.setattr(deals_mod, "talabat_menu", lambda n, f, country="eg": many)
    monkeypatch.setattr("agent1_scout.deals_estimate.estimate_missing_prices", lambda d, n: d)

    out = find_deals("Big Menu", "x", limit=12)
    assert len(out) == 12


@pytest.mark.skipif(not config.RUN_DEALS, reason="set RUN_DEALS=1 for live end-to-end deals")
def test_find_deals_live():
    out = find_deals("Primo's Pizza", "pizza")
    assert isinstance(out, list)
    for d in out:
        assert d.item_name and float(d.price) > 0
