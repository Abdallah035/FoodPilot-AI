"""Food Pilot — Agent 1 (Scout) CLI runner.

Drives the LangGraph agent end-to-end from the terminal, handling the two
human-in-the-loop interrupts (pick restaurant, then pick deal + quantity).

Usage:
    uv run python main.py
    uv run python main.py --query "عايز بيتزا" --location "Maadi, Cairo" --lat 29.96 --lon 31.26
"""

from __future__ import annotations

import argparse
import json
import uuid

from langgraph.types import Command

from agent1_scout.graph import build_graph


def _print_interrupt(payload: dict) -> None:
    print("\n" + "=" * 60)
    print(payload.get("prompt", "Choose an option:"))
    print("=" * 60)
    for opt in payload["options"]:
        if payload["type"] == "select_restaurant":
            print(f"  [{opt['index']}] {opt['name']}")
            print(f"        {opt['reason']}  (score {opt['score']})")
            if opt.get("address"):
                print(f"        📍 {opt['address']}")
            if opt.get("phone"):
                print(f"        📞 {opt['phone']}")
        else:  # select_deal
            desc = f" — {opt['deal_description']}" if opt["deal_description"] else ""
            print(f"  [{opt['index']}] {opt['item_name']} — {opt['price']} {opt['currency']}{desc}")


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


def run(query: str, location: str, lat: float, lon: float) -> dict:
    app = build_graph()
    cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}

    state = {
        "user_query": query,
        "location_query": location,
        "user_coords": {"lat": lat, "lon": lon},
    }

    print(f"\n🍔 Food Pilot — searching for: {query!r} near {location!r}")
    result = app.invoke(state, cfg)

    # ---- INTERRUPT #1: pick a restaurant ----
    payload = result["__interrupt__"][0].value
    _print_interrupt(payload)
    idx = _ask_int("Pick a restaurant number: ", 0, len(payload["options"]) - 1)
    result = app.invoke(Command(resume=idx), cfg)

    # ---- INTERRUPT #2: pick a deal + quantity ----
    payload = result["__interrupt__"][0].value
    if not payload["options"]:
        print("\nNo deals found for this restaurant.")
        return {}
    _print_interrupt(payload)
    deal_idx = _ask_int("Pick a deal number: ", 0, len(payload["options"]) - 1)
    qty = _ask_int("Quantity: ", 1, 99)
    result = app.invoke(Command(resume={"index": deal_idx, "quantity": qty}), cfg)

    # ---- final payload ----
    payload = result["payload"]
    print("\n" + "=" * 60)
    print("✅ FINAL PAYLOAD (handed to the next agent):")
    print("=" * 60)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main() -> None:
    p = argparse.ArgumentParser(description="Food Pilot — Scout agent CLI")
    p.add_argument("--query", default="انا عايز آكل كشري")
    p.add_argument("--location", default="el tahrir , cairo")
    p.add_argument("--lat", type=float, default=29.9600)
    p.add_argument("--lon", type=float, default=31.2600)
    args = p.parse_args()
    run(args.query, args.location, args.lat, args.lon)


if __name__ == "__main__":
    main()
