import pytest

from agent1_scout.state import Coordinates
import main
from main import _resolve_cli_coords


class FakeInterrupt:
    def __init__(self, value):
        self.value = value


class FakeGraph:
    def __init__(self, results):
        self._results = list(results)
        self.calls = []

    def invoke(self, state_or_command, cfg):
        self.calls.append((state_or_command, cfg))
        return self._results.pop(0)


def _interrupt(payload):
    return {"__interrupt__": [FakeInterrupt(payload)]}


def _restaurant_payload(name="Koshary House"):
    return {
        "type": "select_restaurant",
        "prompt": "Choose a restaurant",
        "options": [
            {
                "index": 0,
                "name": name,
                "reason": "nearby",
                "score": 0.9,
                "address": "Tahrir, Cairo",
                "phone": "01000000000",
            }
        ],
    }


def _no_deals_payload(restaurant):
    return {
        "type": "no_deals",
        "prompt": "No menu found",
        "restaurant": restaurant,
        "options": [
            {"index": 0, "label": "Show info", "action": "show_info"},
            {"index": 1, "label": "Choose another", "action": "choose_another"},
        ],
    }


def test_resolve_cli_coords_returns_explicit_coords_without_geocoding():
    def fail_geocoder(location):
        raise AssertionError("geocoder should not be called")

    coords = _resolve_cli_coords("Maadi, Cairo", 29.96, 31.26, geocoder=fail_geocoder)

    assert coords == Coordinates(lat=29.96, lon=31.26)


def test_resolve_cli_coords_geocodes_when_coords_are_missing():
    calls = []

    def fake_geocoder(location):
        calls.append(location)
        return Coordinates(lat=29.9601, lon=31.2569)

    coords = _resolve_cli_coords("Maadi, Cairo", None, None, geocoder=fake_geocoder)

    assert coords == Coordinates(lat=29.9601, lon=31.2569)
    assert calls == ["Maadi, Cairo"]


def test_resolve_cli_coords_rejects_lat_without_lon():
    with pytest.raises(ValueError, match="Pass both --lat and --lon"):
        _resolve_cli_coords("Maadi, Cairo", 29.96, None)


def test_resolve_cli_coords_rejects_lon_without_lat():
    with pytest.raises(ValueError, match="Pass both --lat and --lon"):
        _resolve_cli_coords("Maadi, Cairo", None, 31.26)


def test_resolve_cli_coords_rejects_unresolved_location():
    with pytest.raises(ValueError, match="Could not resolve coordinates for 'Unknown place'"):
        _resolve_cli_coords("Unknown place", None, None, geocoder=lambda location: None)


def test_run_prints_restaurant_info_when_no_deals_show_info(monkeypatch, capsys):
    interrupt_restaurant = {
        "name": "Koshary House",
        "address": "Tahrir, Cairo",
        "phone": "01000000000",
    }
    final_restaurant = {
        **interrupt_restaurant,
        "rating": 4.7,
        "lat": 30.0444,
        "lon": 31.2357,
    }
    graph = FakeGraph(
        [
            _interrupt(_restaurant_payload()),
            _interrupt(_no_deals_payload(interrupt_restaurant)),
            {"selected_restaurant": final_restaurant, "no_deals_action": "show_info"},
        ]
    )
    answers = iter([0, 0])

    monkeypatch.setattr(main, "build_graph", lambda: graph)
    monkeypatch.setattr(main, "_ask_int", lambda prompt, lo, hi: next(answers))

    result = main.run("عايز كشري", "Tahrir, Cairo", 30.0444, 31.2357)
    output = capsys.readouterr().out

    assert result == {"status": "menu_not_found", "restaurant_info": final_restaurant}
    assert "RESTAURANT INFO" in output
    assert "Restaurant: Koshary House" in output
    assert "Address: Tahrir, Cairo" in output
    assert "Phone: 01000000000" in output
    assert "Rating: 4.7" in output
    assert "Coordinates: 30.0444, 31.2357" in output


def test_run_no_deals_choose_another_loops_to_restaurant_selection(monkeypatch, capsys):
    first_restaurant = {
        "name": "Koshary House",
        "address": "Tahrir, Cairo",
        "phone": "01000000000",
    }
    scout_payload = {
        "order_status": "configured",
        "user_intent": "burger",
        "selected_restaurant": {"name": "Burger House"},
        "selected_deal": {"item_name": "Burger", "quantity": 1},
    }
    graph = FakeGraph(
        [
            _interrupt(_restaurant_payload()),
            _interrupt(_no_deals_payload(first_restaurant)),
            _interrupt(_restaurant_payload(name="Burger House")),
            _interrupt(
                {
                    "type": "select_deal",
                    "prompt": "Choose a deal",
                    "options": [
                        {
                            "index": 0,
                            "item_name": "Burger",
                            "price": "120",
                            "currency": "EGP",
                            "deal_description": "combo",
                            "portion": None,
                        }
                    ],
                }
            ),
            {"payload": scout_payload},
        ]
    )
    answers = iter([0, 1, 0, 0, 1])
    pipeline_result = {"status": "ok"}

    monkeypatch.setattr(main, "build_graph", lambda: graph)
    monkeypatch.setattr(main, "_ask_int", lambda prompt, lo, hi: next(answers))
    monkeypatch.setattr(main, "run_post_scout_pipeline", lambda payload, rag_enabled=True: pipeline_result)
    monkeypatch.setattr(main, "print_pipeline_result", lambda result: None)

    result = main.run("عايز برجر", "Maadi, Cairo", 29.96, 31.26)
    output = capsys.readouterr().out

    assert result == pipeline_result
    assert "Burger House" in output
    assert "RESTAURANT INFO" not in output
