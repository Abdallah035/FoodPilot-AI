"""Task 1 — unit tests for the State schema."""

from agent1_scout.state import (
    Coordinates,
    Deal,
    OrderPayload,
    Restaurant,
    SelectedRestaurant,
)


def _sample_restaurant() -> Restaurant:
    return Restaurant(
        name="Burger Joint",
        address="123 Main Street",
        coordinates=Coordinates(lat=31.2001, lon=29.9187),
        rating=4.7,
        reviews=2000,
        price_level="$$",
    )


def _sample_deal() -> Deal:
    return Deal(
        item_name="Double Smashburger Combo",
        price="250",
        currency="EGP",
        deal_description="Includes medium fries and a drink.",
        source_url="https://example-restaurant-menu-link.com",
        quantity=2,
        portion="300g",
    )


def test_restaurant_instantiation():
    r = _sample_restaurant()
    assert r.name == "Burger Joint"
    assert r.coordinates.lat == 31.2001
    assert r.rating == 4.7
    # optional scoring fields default to None until scoring runs
    assert r.score is None
    assert r.distance_km is None


def test_deal_has_quantity_and_portion():
    d = _sample_deal()
    assert d.quantity == 2
    assert d.portion == "300g"


def test_deal_defaults():
    d = Deal(item_name="Plain Burger")
    assert d.quantity == 1  # default one item
    assert d.portion == ""  # unknown size by default
    assert d.currency == "EGP"


def test_order_payload_matches_spec_shape():
    r = _sample_restaurant()
    d = _sample_deal()
    payload = OrderPayload(
        user_intent="burger",
        selected_restaurant=SelectedRestaurant(
            name=r.name,
            address=r.address,
            coordinates=r.coordinates,
            google_maps_rating=r.rating,
        ),
        selected_deal=d,
    )
    dumped = payload.model_dump()

    # top-level keys exactly match the spec §5
    assert set(dumped.keys()) == {
        "order_status",
        "user_intent",
        "selected_restaurant",
        "selected_deal",
    }
    assert dumped["order_status"] == "configured"
    assert dumped["selected_restaurant"]["google_maps_rating"] == 4.7
    assert dumped["selected_restaurant"]["coordinates"] == {"lat": 31.2001, "lon": 29.9187}
    assert dumped["selected_deal"]["item_name"] == "Double Smashburger Combo"
    # new fields carried through
    assert dumped["selected_deal"]["quantity"] == 2
    assert dumped["selected_deal"]["portion"] == "300g"
