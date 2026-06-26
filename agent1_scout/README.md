# Agent 1 — Discovery / Scout (Finder + Picker)

LangGraph agent that turns a vague craving (Egyptian Arabic or English) into a
**selected restaurant** and a **selected deal + quantity**, then outputs a strict
JSON payload for the next agent.

## Flow

```
START
  -> find_restaurants     Apify Google Maps + scoring -> top 3
  -> ask_user_restaurant  INTERRUPT #1: user picks a restaurant
  -> find_deals_node      Talabat (by slug) -> Tavily web -> LLM estimate
  -> ask_user_deal        INTERRUPT #2: user picks a deal + sets quantity
  -> compile_payload      build the JSON payload
END
```

## Scoring (rank restaurants)

| Criteria | Weight | Logic |
|---|---|---|
| Proximity | 40% | Haversine distance, nearer = higher |
| Credibility | 50% | `(rating/5) × min(1, log10(reviews+1)/4)` — high rating AND many reviews |
| Price match | 10% | restaurant price tier vs the user's budget |

## Accurate menu prices (Egypt)

1. **Talabat by slug** — Tavily finds the exact `talabat.com/egypt/<slug>` URL,
   then Apify scrapes that exact restaurant's live menu. Avoids wrong-restaurant
   matches; junk (0 EGP) items dropped.
2. **Tavily open-web fallback** — if the place isn't on Talabat.
3. **LLM estimate** — fills any missing price, flagged `(estimated price)`.

## Run

```bash
# install
uv sync

# copy env and fill keys: GROQ_API_KEY, APIFY_API_TOKEN, TAVILY_API_KEY, LANGSMITH_API_KEY
cp .env.example .env

# run the CLI (defaults to an Arabic koshary craving)
uv run python main.py
uv run python main.py --query "I'm craving a good burger" --location "Maadi, Cairo" --lat 29.96 --lon 31.26
```

## Tests

```bash
uv run pytest                 # fast suite (external calls mocked)

# opt-in live tests (hit real APIs):
RUN_APIFY=1   uv run pytest tests/test_discovery.py
RUN_TALABAT=1 uv run pytest tests/test_deals_talabat.py
RUN_TAVILY=1  uv run pytest tests/test_deals_fallback.py
RUN_DEALS=1   uv run pytest tests/test_find_deals.py
RUN_LIVE=1    uv run pytest tests/test_nodes.py
RUN_TRACE=1   uv run pytest tests/test_tracing.py
```

## Manual inspection scripts

```bash
uv run python -m scripts.inspect_discovery "burger" "Maadi, Cairo" 5
uv run python -m scripts.inspect_deals "Primo's Pizza" "pizza" eg
```

## Output payload (spec §5)

```json
{
  "order_status": "configured",
  "user_intent": "burger",
  "selected_restaurant": {
    "name": "...", "address": "...", "phone": "...",
    "coordinates": {"lat": 0, "lon": 0},
    "google_maps_rating": 4.6
  },
  "selected_deal": {
    "item_name": "...", "price": "250", "currency": "EGP",
    "deal_description": "...", "source_url": "...",
    "quantity": 2, "portion": ""
  }
}
```
