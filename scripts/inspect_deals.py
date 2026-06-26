"""Manual inspection: accurate Talabat menu via Tavily-slug, with YOUR OWN query.

Edit the variables below (or pass args) and run:
    uv run python -m scripts.inspect_deals
    uv run python -m scripts.inspect_deals "Buffalo Burger" burger eg
    uv run python -m scripts.inspect_deals "كشري التحرير" كشري eg

Shows: the Talabat slug Tavily found, then the live menu scraped for THAT exact
restaurant. Writes:
    deals_raw.json     — raw Talabat restaurant + menu_items (for the slug)
    deals_mapped.json  — clean Deal objects
"""

from __future__ import annotations

import json
import sys

from apify_client import ApifyClient

import config
from agent1_scout.deals import (
    TALABAT_ACTOR_ID,
    _dedupe,
    _filter_relevant,
    _map_menu_item,
    find_talabat_slug,
)
from agent1_scout.discovery import _dataset_id


def main() -> None:
    # defaults (override via CLI args)
    restaurant = "كشري التحرير"
    food = "كشري"
    country = "eg"
    if len(sys.argv) > 1:
        restaurant = sys.argv[1]
    if len(sys.argv) > 2:
        food = sys.argv[2]
    if len(sys.argv) > 3:
        country = sys.argv[3]

    print(f"Restaurant: '{restaurant}'  (food filter: '{food or '-'}')  country={country}")

    # Step 1 — Tavily finds the exact Talabat slug
    print("\n[1] Tavily -> Talabat slug ...")
    slug = find_talabat_slug(restaurant)
    print(f"    slug = {slug!r}")
    if not slug:
        print("    No Talabat page found -> would FALL BACK to Tavily web extract / estimate.")
        json.dump([], open("deals_raw.json", "w", encoding="utf-8"))
        json.dump([], open("deals_mapped.json", "w", encoding="utf-8"))
        return

    # Step 2 — scrape that exact restaurant by slug
    print(f"\n[2] Apify Talabat scrape by slug '{slug}' ...")
    client = ApifyClient(config.APIFY_API_TOKEN)
    run = client.actor(TALABAT_ACTOR_ID).call(
        run_input={
            "restaurantSlugs": [slug],
            "country": country,
            "scrapeMenu": True,
            "maxResults": 1,
        }
    )
    raw = list(client.dataset(_dataset_id(run)).iterate_items())

    deals = []
    for r in raw:
        print(f"    -> scraped restaurant: {r.get('name')!r}  ({len(r.get('menu_items', []) or [])} items)")
        for item in r.get("menu_items", []) or []:
            d = _map_menu_item(item, food)
            if d is not None:
                deals.append(d)
    mapped = [d.model_dump() for d in _filter_relevant(_dedupe(deals), food)]

    json.dump(raw, open("deals_raw.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(mapped, open("deals_mapped.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\nMapped (clean, relevant) deals: {len(mapped)} -> deals_mapped.json")
    for m in mapped[:30]:
        print(f"  - {m['item_name']} | {m['price']} {m['currency']}")


if __name__ == "__main__":
    main()
