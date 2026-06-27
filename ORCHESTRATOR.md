# Food Pilot — Orchestrator

`orchestrator.py` is the top-level brain of the **Food Pilot** multi-agent system. It receives a raw user message, decides what the user wants, and routes execution across the other agents and pipelines in the correct order.

---

## How It Fits in the System

```
YOU (chat)
    │
    ▼
orchestrator.py          ← this file (the manager)
    │
    ├─── agent1_scout/   ← finds restaurants + deals (2 HITL interrupts)
    ├─── RAG/Rag.py      ← answers food questions / filters by calories
    └─── order_finalizer/ ← applies promos, calculates price, prints receipt
```

The orchestrator never talks directly to external APIs. It delegates to each sub-agent or RAG function and stitches the results together into a final user-facing response.

---

## Routing Modes

The classifier node reads the user's message and assigns one of four modes:

| Mode | Trigger | Pipeline |
|------|---------|----------|
| **A — Order** | User wants to order food from a restaurant | `classify → scout → enrich → order → END` |
| **B — Food Inquiry** | User asks about a dish (calories, ingredients, description) | `classify → food_inquiry → END` |
| **C — Calorie Filter + Order** | User wants food under a calorie limit AND wants to order | `classify → calorie_filter → scout → order → END` |
| **UNCLEAR** | Not enough information to route | `classify → clarify (HITL) → classify → …` |

---

## The Graph

Built with **LangGraph** (`StateGraph`). The compiled graph (`build_orchestrator_graph`) is the one used at runtime.

```
START
  │
  ▼
classify ──────────────────────────────────────────┐
  │                                                │
  ├─ mode=A ──► scout ──► enrich ──► order ──► END │
  │                                                │
  ├─ mode=B ──► food_inquiry ──────────────► END   │
  │                                                │
  ├─ mode=C ──► calorie_filter ──► scout ──► order ──► END
  │
  └─ UNCLEAR ──► clarify (HITL) ──► classify (loop back)
```

`build_orchestrator` (the first function) contains a simpler version with an unconditional `scout → enrich` edge and exists for reference. `build_orchestrator_graph` is the correct version: after `scout` it conditionally routes to `enrich` (Mode A) or skips straight to `order` (Mode C).

---

## Nodes

### `node_classify`
Calls the Azure OpenAI LLM with a structured prompt that returns JSON:
```json
{ "mode": "A|B|C|UNCLEAR", "what": "...", "where": "...", "clarification": "..." }
```
Extracts the food entity/description (`what`) and location (`where`) for use by downstream nodes.

### `node_clarify`
Issues a LangGraph `interrupt()` — the graph freezes and surfaces a question to the caller. The caller resumes with `Command(resume=answer)`. The answer is appended to the original message and fed back into `node_classify`.

### `node_food_inquiry` (Mode B)
Calls `food_agent(dish_name=...)` which delegates to `RAG/Rag.py → query_rag()`. Returns a natural-language answer about the dish and stores it in `rag_answer` / `final_output`.

### `node_calorie_filter` (Mode C, step 1)
Calls `food_agent(calorie_constraint=...)` which delegates to `RAG/Rag.py → find_dishes_by_calorie_constraint()`. Stores matching dish names in `rag_matches` and the numeric limit in `calorie_limit`.

### `node_scout`
Drives the **agent1_scout** LangGraph to completion. Handles the scout's own two HITL interrupts inline (restaurant selection, deal selection) via a stdin loop. In Mode C it uses the top calorie match as the search target instead of the raw user query. Stores the final payload in `scout_payload`.

### `node_enrich` (Mode A only)
Calls `food_agent(payload=...)` which delegates to `RAG/Rag.py → calculate_order_calories()` to add calorie data for the chosen deal. Merges the enrichment result back into `scout_payload` under the key `rag_enrichment` so the order finalizer can include it in the receipt.

### `node_order`
Drives the **order_finalizer** LangGraph: searches for promos, verifies them, calculates final price, and generates a receipt. Stores the result in `order_result` / `final_output`.

---

## State (`OrchestratorState`)

All nodes read from and write to a shared `TypedDict`:

| Key | Type | Set by |
|-----|------|--------|
| `user_message` | `str` | caller / `node_clarify` |
| `mode` | `str` | `node_classify` |
| `what` | `str` | `node_classify` |
| `where` | `str` | `node_classify` |
| `calorie_limit` | `float` | `node_calorie_filter` |
| `rag_matches` | `list` | `node_calorie_filter` |
| `rag_answer` | `str` | `node_food_inquiry` |
| `scout_payload` | `dict` | `node_scout` / `node_enrich` |
| `enriched_result` | `dict` | `node_enrich` |
| `order_result` | `dict` | `node_order` |
| `clarification_question` | `str` | `node_classify` |
| `final_output` | `str` | `node_food_inquiry` / `node_order` |

---

## Agent Wrappers

The three wrapper functions act as the seam between the orchestrator and each sub-agent. Each one is currently wired to the real sub-agents but includes a fallback stub in case the sub-agent raises an exception.

### `scout_agent(what, where, state)`
Imports and invokes `agent1_scout.graph.build_graph()`. Drives the scout graph through its two HITL interrupts by reading from stdin. Returns `{ restaurant, deal, payload }`.

### `food_agent(dish_name, calorie_constraint, payload)`
Routes to one of three `RAG/Rag.py` functions depending on which argument is provided:
- `dish_name` → `query_rag()` (Mode B)
- `calorie_constraint` → `find_dishes_by_calorie_constraint()` (Mode C)
- `payload` → `calculate_order_calories()` (Mode A enrichment)

### `order_agent(payload)`
Imports and invokes `order_finalizer.graph.build_graph()`. Returns `{ summary, promo_applied, final_price }`.

---

## Relation to Other Modules

| Module | Role | Called via |
|--------|------|-----------|
| `agent1_scout/` | Finds and ranks restaurants, scrapes live deals, presents HITL choices | `scout_agent()` wrapper |
| `RAG/Rag.py` | ChromaDB vector store over Egyptian dish data; answers food queries and calorie lookups | `food_agent()` wrapper |
| `order_finalizer/` | Searches promos, verifies them with LLM, calculates price, prints receipt | `order_agent()` wrapper |
| `config.py` | Provides `get_azure_openai_llm()` used by the classifier | direct import |

The RAG pipeline (`build_rag_pipeline`) is initialized **once at import time** and shared across all calls to `food_agent`.

---

## Running It

### As a CLI

```bash
# Single message
python orchestrator.py "I want a burger near Maadi"

# Interactive mode (Ctrl+C to quit)
python orchestrator.py
```

### Programmatically

```python
from orchestrator import run_orchestrator

response = run_orchestrator("What are the ingredients in koshari?")
print(response)
```

`run_orchestrator` builds a fresh compiled graph, invokes it, and handles any `clarify` interrupts via stdin before returning `final_output` as a string.

---

## Environment Variables

The orchestrator inherits all keys required by its sub-agents. Minimum set for the orchestrator's own LLM (classifier):

```
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT_NAME
AZURE_OPENAI_API_VERSION
```

Sub-agent keys (`APIFY_API_TOKEN`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY`) are also needed when those nodes execute. See [README.md](README.md) for the full list.

---

## LangSmith Tracing

Set at startup:
```python
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=food-pilot   # override via LANGCHAIN_PROJECT env var
```

Every node invocation, LLM call, and tool call is traced automatically.
