"""Food Pilot CLI runner.

Runs the integrated pipeline:
    Scout -> RAG nutrition enrichment -> order finalizer.

Usage:
    uv run python main.py
    uv run python main.py --query "عايز بيتزا" --location "Maadi, Cairo"
    uv run python main.py --query "عايز بيتزا" --location "Maadi, Cairo" --lat 29.96 --lon 31.26
    uv run python main.py --skip-rag
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Callable

from langgraph.types import Command

from agent1_scout.discovery import geocode_location
from agent1_scout.state import Coordinates
from agent1_scout.graph import build_graph
from pipeline import print_pipeline_result, run_post_scout_pipeline


def _print_interrupt(payload: dict) -> None:
    print("\n" + "=" * 60)
    print(payload.get("prompt", "Choose an option:"))
    print("=" * 60)
    if payload["type"] == "no_deals":
        restaurant = payload.get("restaurant", {})
        print(f"\nRestaurant: {restaurant.get('name', '')}")
        print(f"Address: {restaurant.get('address') or 'Not available'}")
        print(f"Phone: {restaurant.get('phone') or 'Not available'}")

    for opt in payload["options"]:
        if payload["type"] == "select_restaurant":
            print(f"  [{opt['index']}] {opt['name']}")
            print(f"        {opt['reason']}  (score {opt['score']})")
            if opt.get("address"):
                print(f"        Location: {opt['address']}")
            if opt.get("phone"):
                print(f"        Phone: {opt['phone']}")
        elif payload["type"] == "select_deal":
            desc = f" - {opt['deal_description']}" if opt["deal_description"] else ""
            portion = f" - الحجم: {opt['portion']}" if opt.get("portion") else ""
            print(f"  [{opt['index']}] {opt['item_name']} - السعر: {opt['price']} {opt['currency']}{desc}{portion}")
        elif payload["type"] == "no_deals":
            print(f"  [{opt['index']}] {opt['label']}")


def _print_restaurant_info_result(restaurant: dict) -> None:
    print("\n" + "=" * 60)
    print("RESTAURANT INFO")
    print("=" * 60)
    print(f"Restaurant: {restaurant.get('name') or 'Not available'}")
    print(f"Address: {restaurant.get('address') or 'Not available'}")
    print(f"Phone: {restaurant.get('phone') or 'Not available'}")

    rating = restaurant.get("rating")
    if rating is not None:
        print(f"Rating: {rating}")

    lat = restaurant.get("lat")
    lon = restaurant.get("lon")
    if lat is not None and lon is not None:
        print(f"Coordinates: {lat}, {lon}")


def _ask_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(f"  Please enter a number between {lo} and {hi}.")


def _resolve_cli_coords(
    location: str,
    lat: float | None,
    lon: float | None,
    geocoder: Callable[[str], Coordinates | None] = geocode_location,
) -> Coordinates:
    """Return explicit CLI coordinates or resolve the location text."""
    if (lat is None) != (lon is None):
        raise ValueError("Pass both --lat and --lon, or omit both to resolve --location.")

    if lat is not None and lon is not None:
        return Coordinates(lat=lat, lon=lon)

    coords = geocoder(location)
    if coords is None:
        raise ValueError(
            f"Could not resolve coordinates for {location!r}; pass --lat and --lon explicitly."
        )
    return coords


def run(query: str, location: str, lat: float, lon: float, *, rag_enabled: bool = True) -> dict:
    scout_app = build_graph()
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}

    state = {
        "user_query": query,
        "location_query": location,
        "user_coords": {"lat": lat, "lon": lon},
    }

    print(f"\n🍔 Food Pilot — searching for: {query!r} near {location!r}")
    result = scout_app.invoke(state, cfg)

    # ---- INTERRUPT #1: pick a restaurant ----
    payload = result["__interrupt__"][0].value
    _print_interrupt(payload)
    idx = _ask_int("Pick a restaurant number: ", 0, len(payload["options"]) - 1)
    result = scout_app.invoke(Command(resume=idx), cfg)

    # ---- INTERRUPT #2: pick a deal + quantity, or handle missing menu ----
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        _print_interrupt(payload)

        if payload["type"] == "select_deal":
            deal_idx = _ask_int("Pick a deal number: ", 0, len(payload["options"]) - 1)
            qty = _ask_int("Quantity: ", 1, 99)
            result = scout_app.invoke(Command(resume={"index": deal_idx, "quantity": qty}), cfg)
            break

        if payload["type"] == "select_restaurant":
            idx = _ask_int("Pick a restaurant number: ", 0, len(payload["options"]) - 1)
            result = scout_app.invoke(Command(resume=idx), cfg)
            continue

        if payload["type"] == "no_deals":
            action_idx = _ask_int("Pick an option: ", 0, len(payload["options"]) - 1)
            result = scout_app.invoke(Command(resume=action_idx), cfg)
            if "__interrupt__" not in result:
                restaurant = result.get("selected_restaurant") or payload.get("restaurant", {})
                _print_restaurant_info_result(restaurant)
                return {"status": "menu_not_found", "restaurant_info": restaurant}

    # ---- Scout payload -> RAG -> order finalizer ----
    scout_payload = result["payload"]
    print("\n" + "=" * 60)
    print("SCOUT PAYLOAD")
    print("=" * 60)
    print(json.dumps(scout_payload, ensure_ascii=False, indent=2))

    integrated_result = run_post_scout_pipeline(scout_payload, rag_enabled=rag_enabled)
    print_pipeline_result(integrated_result)
    return integrated_result


def main() -> None:
    p = argparse.ArgumentParser(description="Food Pilot integrated CLI")
    p.add_argument("--query", default="انا عايز آكل كشري")
    p.add_argument("--location", default="el tahrir , cairo")
    p.add_argument("--lat", type=float, default=None)
    p.add_argument("--lon", type=float, default=None)
    p.add_argument("--skip-rag", action="store_true", help="Skip RAG nutrition enrichment and go directly to finalizer")
    args = p.parse_args()
    try:
        coords = _resolve_cli_coords(args.location, args.lat, args.lon)
    except (RuntimeError, ValueError) as exc:
        p.error(str(exc))

    print(f"Resolved coordinates for {args.location!r}: lat={coords.lat}, lon={coords.lon}")
    run(args.query, args.location, coords.lat, coords.lon, rag_enabled=not args.skip_rag)


if __name__ == "__main__":
    main()
