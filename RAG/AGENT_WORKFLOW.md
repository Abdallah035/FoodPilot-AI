# RAG Calorie Agent — Workflow

## Role in the Pipeline

This agent sits between the **Order Finder Agent** (which selects a restaurant and deal) and the **next agent** (which uses calorie data for recommendations or health decisions).

```
[Order Finder Agent]
        |
        v
[RAG Calorie Agent]  ← this agent
        |
        v
[Next Agent]
```

---

## Input

The agent receives the full JSON from the previous agent:

```json
{
  "order_status": "configured",
  "user_intent": "كشري",
  "selected_restaurant": { ... },
  "selected_deal": {
    "item_name": "علبة توب",
    "quantity": 7,
    "portion": ""
  }
}
```

Key fields used:
- `user_intent` → dish name for RAG lookup
- `selected_deal.quantity` + `selected_deal.item_name` + `selected_deal.portion` → quantity expression

---

## Workflow Steps

### Step 1 — Quantity Parsing
The agent builds a descriptive quantity string from the deal fields:

```
quantity + item_name + portion + user_intent
→ "7 علبة توب كشري"
```

This string is sent to the **LLM (Groq / LLaMA 3.3)** which understands Egyptian context:

| Expression | Grams |
|------------|-------|
| ربع كيلو | 250g |
| نص كيلو | 500g |
| رغيف / عيش | 80g |
| طبق / صحن | ~350g (varies by dish) |
| علبة | ~200g |
| وجبة | estimated by dish type |
| كبير / وسط / صغير | adjusts the base estimate |

---

### Step 2 — RAG Lookup
The dish name (`user_intent`) is searched in ChromaDB using two strategies:

```
1. Exact metadata match  →  fast, O(1), no embedding
         ↓ if miss
2. Semantic search       →  catches transliterations
                             e.g. "Om Ali" → "أم علي"
                             threshold: cosine distance < 0.60
         ↓ if miss
3. Web Search Fallback   →  DuckDuckGo (English + Arabic queries)
                             LLM extracts cal/100g from results
                             Result is saved to RAG for future use
```

---

### Step 3 — Calorie Calculation

```
total_calories = (calories_per_100g / 100) × quantity_grams
```

---

### Step 4 — Output

The original JSON is returned intact with `calorie_info` appended:

```json
{
  "order_status": "configured",
  "user_intent": "كشري",
  "selected_restaurant": { ... },
  "selected_deal": { ... },
  "calorie_info": {
    "quantity_grams": 1400.0,
    "calories_per_100g": 140.0,
    "total_calories": 1960.0,
    "found": true,
    "source": "rag"
  }
}
```

`source` values:
- `"rag"` — found in local ChromaDB
- `"web"` — found via web search and saved to RAG
- `null` — not found anywhere

---

## Knowledge Base

- **data.json** — 100+ Egyptian and international dishes with `calories_per_100g`
- **ChromaDB** (`chroma_dishes_db/`) — vector store built from data.json, persisted to disk
- **Embedding model** — `paraphrase-multilingual-mpnet-base-v2` (supports Arabic + English)
- **LLM** — `llama-3.3-70b-versatile` via Groq API

New dishes discovered via web search are automatically appended to both `data.json` and ChromaDB, so the knowledge base grows over time.

---

## Key Files

| File | Purpose |
|------|---------|
| `Rag.py` | Agent logic |
| `data.json` | Dish calorie database |
| `chroma_dishes_db/` | Persisted vector store (auto-generated) |
| `test_agent.py` | Test the agent with sample orders |

---

## Environment Variables Required

```
GROQ_API_KEY=...       # LLM for quantity parsing + calorie extraction
```
