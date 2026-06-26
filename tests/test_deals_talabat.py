"""Task 8a — tests for the accurate Talabat menu (Tavily-slug + scrape).

Covers: slug extraction from real Talabat URL formats, junk-price filtering,
item mapping, dedupe, relevance filter. Live calls gated by RUN_TALABAT=1.
"""

import os

import pytest

from agent1_scout.deals import (
    _dedupe,
    _filter_relevant,
    _has_real_price,
    _map_menu_item,
    _price_to_str,
    find_talabat_slug,
    slug_from_talabat_url,
    talabat_menu,
)
from agent1_scout.state import Deal


# --- slug extraction (the accuracy fix) --------------------------------------
def test_slug_simple_url():
    assert slug_from_talabat_url("https://www.talabat.com/egypt/primos-pizza-marina-5") == "primos-pizza-marina-5"


def test_slug_restaurant_id_url():
    # talabat.com/egypt/restaurant/<id>/<slug>?aid=...
    url = "https://www.talabat.com/egypt/restaurant/649813/primo-abbasiya?aid=7753"
    assert slug_from_talabat_url(url) == "primo-abbasiya"


def test_slug_keeps_complex_segment():
    url = "https://www.talabat.com/egypt/restaurant/736579/primos-pizza-marina-4--5--6--7?aid=10342"
    assert slug_from_talabat_url(url) == "primos-pizza-marina-4--5--6--7"


def test_slug_none_for_bad_url():
    assert slug_from_talabat_url("https://www.talabat.com/") is None
    assert slug_from_talabat_url("") is None


# --- price handling ----------------------------------------------------------
def test_price_normalisation():
    assert _price_to_str(250) == "250"
    assert _price_to_str(180.0) == "180"
    assert _price_to_str("EGP 220") == "220"
    assert _price_to_str("1,250.50") == "1250.50"
    assert _price_to_str(None) == ""


def test_has_real_price():
    assert _has_real_price("250")
    assert not _has_real_price("0")
    assert not _has_real_price("")


def test_map_item_skips_zero_price():
    # junk rows that polluted earlier output
    assert _map_menu_item({"name": "Grilled Kofta", "price": 0}) is None
    assert _map_menu_item({"name": "Kebab", "price": "0"}) is None


def test_map_item_real_and_arabic():
    d = _map_menu_item({"name": "Double Beef Burger", "price": 250, "description": "cheese"}, "burger")
    assert isinstance(d, Deal) and d.price == "250" and d.currency == "EGP"
    ar = _map_menu_item({"name": "علبة كشري كبيرة", "price": "45", "description": "أرز ومكرونة"}, "كشري")
    assert ar.item_name == "علبة كشري كبيرة" and ar.price == "45"


# --- dedupe + relevance ------------------------------------------------------
def test_dedupe():
    deals = [
        Deal(item_name="Kofta Meal", price="271"),
        Deal(item_name="Kofta Meal", price="271"),
        Deal(item_name="Kofta Meal", price="339"),
    ]
    assert len(_dedupe(deals)) == 2


def test_filter_relevant_and_fallback():
    deals = [Deal(item_name="Margherita Pizza", price="120"), Deal(item_name="Coca-Cola", price="25")]
    assert [d.item_name for d in _filter_relevant(deals, "pizza")] == ["Margherita Pizza"]
    assert len(_filter_relevant(deals, "sushi")) == 2  # no match -> keep all


# --- the user-selection contract (HITL #2 will consume these) ---------------
def test_deals_are_selectable_with_quantity():
    """Each returned deal must be pickable and accept a user quantity."""
    deals = [
        Deal(item_name="Chicken Ranch Pizza", price="160", deal_description="medium"),
        Deal(item_name="Margherita Pizza", price="120"),
    ]
    clean = _filter_relevant(_dedupe(deals), "pizza")
    assert len(clean) >= 1
    for d in clean:
        assert d.item_name and float(d.price) > 0   # shows name + real price
        assert d.quantity == 1                       # default qty, user can change
    # simulate the user picking item 0 and setting quantity = 3
    chosen = clean[0].model_copy(update={"quantity": 3})
    assert chosen.quantity == 3
    assert chosen.item_name == "Chicken Ranch Pizza"


# --- live (gated) ------------------------------------------------------------
@pytest.mark.skipif(os.getenv("RUN_TALABAT") != "1", reason="set RUN_TALABAT=1 to hit Tavily+Talabat")
def test_talabat_menu_live():
    deals = talabat_menu("Primo's Pizza", "pizza", country="eg")
    assert isinstance(deals, list)
    for d in deals:
        assert float(d.price) > 0  # no junk prices
