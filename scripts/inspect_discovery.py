"""Manual inspection: run the Apify discovery actor live and dump results.

Usage:
    uv run python scripts/inspect_discovery.py "burger" "Maadi, Cairo" 5

Writes two files in the project root:
    discovery_raw.json     — raw Apify actor items
    discovery_mapped.json  — mapped Restaurant objects
"""

from __future__ import annotations

import json
import sys

from apify_client import ApifyClient

import config
from agent1_scout.discovery import ACTOR_ID, _dataset_id, _map_place


def main() -> None:
    food = sys.argv[1] if len(sys.argv) > 1 else "burger"
    location = sys.argv[2] if len(sys.argv) > 2 else "Maadi, Cairo"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"Searching Apify: '{food}' near '{location}' (n={n}) ...")
    client = ApifyClient(config.APIFY_API_TOKEN)
    run = client.actor(ACTOR_ID).call(
        run_input={
            "searchStringsArray": [f"{food} restaurant {location}"],
            "maxCrawledPlacesPerSearch": n,
            "skipClosedPlaces": True,
            "language": "en",
        }
    )

    raw = list(client.dataset(_dataset_id(run)).iterate_items())
    mapped = [r.model_dump() for r in (_map_place(p) for p in raw) if r is not None]

    with open("discovery_raw.json", "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)
    with open("discovery_mapped.json", "w", encoding="utf-8") as f:
        json.dump(mapped, f, ensure_ascii=False, indent=2)

    print(f"Raw items: {len(raw)}  ->  discovery_raw.json")
    print(f"Mapped restaurants: {len(mapped)}  ->  discovery_mapped.json")
    for m in mapped:
        print(f"  - {m['name']} | {m['rating']}* ({m['reviews']} reviews) | {m['price_level']}")


if __name__ == "__main__":
    main()
