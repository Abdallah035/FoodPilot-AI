"""Food Pilot — Orchestrator

LangGraph multi-agent orchestrator that routes user messages to the right pipeline:
  Mode A — Order:          classify → scout (HITL) → enrich → order → END
  Mode B — Food Inquiry:   classify → food_inquiry (RAG) → END
  Mode C — Calorie Filter: classify → calorie_filter → scout (HITL) → order → END
  UNCLEAR:                 classify → clarify (HITL) → classify → ...
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Literal, Optional, TypedDict

from dotenv import load_dotenv

load_dotenv()

# ── LangSmith tracing ──────────────────────────────────────────────────────
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", os.getenv("LANGCHAIN_PROJECT", "food-pilot"))

# ── ensure project root is on path ─────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

import config

# ── RAG pipeline (initialised once at import time) ─────────────────────────
_RAG_JSON = os.path.join(_ROOT, "RAG", "data.json")
_RAG_CHROMA = os.path.join(_ROOT, "RAG", "chroma_dishes_db")

from RAG.Rag import (
    build_rag_pipeline,
    calculate_order_calories,
    find_dishes_by_calorie_constraint,
    query_rag,
)

print("[Orchestrator] Initialising RAG pipeline…")
_vectorstore, _llm_rag, _all_dishes = build_rag_pipeline(
    json_path=_RAG_JSON,
    persist_dir=_RAG_CHROMA,
)
print("[Orchestrator] RAG pipeline ready.")

# ── Orchestrator LLM ───────────────────────────────────────────────────────
_llm = config.get_azure_openai_llm(temperature=0.0)


# ═══════════════════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════════════════

class OrchestratorState(TypedDict, total=False):
    user_message: str
    mode: str                       # "A" | "B" | "C" | "UNCLEAR"
    what: str                       # food entity / dish name / calorie description
    where: str                      # location string (Modes A & C)
    calorie_limit: Optional[float]  # parsed limit in kcal (Mode C)
    rag_matches: list               # dish names under calorie limit (Mode C)
    rag_answer: str                 # RAG answer text (Mode B)
    scout_payload: dict             # OrderPayload dict from Scout agent
    enriched_result: dict           # calorie enrichment from food_agent (Mode A)
    order_result: dict              # receipt/price from order_finalizer
    clarification_question: str     # question asked during UNCLEAR
    final_output: str               # user-facing response


# ═══════════════════════════════════════════════════════════════════════════
# PLACEHOLDER AGENT WRAPPERS  (TODO: replace with real module calls)
# ═══════════════════════════════════════════════════════════════════════════

def scout_agent(what: str, where: str, state: dict) -> dict:
    """
    TODO: wire to the real agent1_scout graph.

    Drives the Scout LangGraph to completion, handling its two HITL interrupts
    (restaurant selection + deal selection) by prompting the user on stdin.

    Returns: { "restaurant": {...}, "deal": {...}, "payload": {...} }
    """
    try:
        from langgraph.types import Command as Cmd
        from agent1_scout.graph import build_graph as build_scout_graph

        print(f"\n[Scout] Starting scout for '{what}' near '{where}'")

        scout_app = build_scout_graph()
        thread = {"configurable": {"thread_id": f"scout-{id(state)}"}}

        initial = {
            "user_query": state.get("user_message", what),
            "location_query": where,
            "user_coords": state.get("user_coords", {"lat": 30.0444, "lon": 31.2357}),
        }

        result = scout_app.invoke(initial, thread)

        # drive through HITL interrupts until the graph finishes
        while "__interrupt__" in result:
            interrupt_val = result["__interrupt__"][0].value
            itype = interrupt_val.get("type", "unknown")

            if itype == "select_restaurant":
                print(f"\n[Scout HITL] {interrupt_val['prompt']}")
                for opt in interrupt_val["options"]:
                    print(f"  [{opt['index']}] {opt['name']} — {opt.get('reason', '')}")
                choice = input("Enter number: ").strip()
                result = scout_app.invoke(Cmd(resume=int(choice)), thread)

            elif itype == "select_deal":
                print(f"\n[Scout HITL] {interrupt_val['prompt']}")
                for opt in interrupt_val["options"]:
                    print(f"  [{opt['index']}] {opt['item_name']} — {opt.get('price', '')} {opt.get('currency', '')}")
                idx = int(input("Enter number: ").strip())
                qty = int(input("Enter quantity (default 1): ").strip() or "1")
                result = scout_app.invoke(Cmd(resume={"index": idx, "quantity": qty}), thread)

            elif itype == "no_deals":
                print(f"\n[Scout HITL] {interrupt_val['prompt']}")
                for opt in interrupt_val["options"]:
                    print(f"  [{opt['index']}] {opt['label']}")
                choice = int(input("Enter number: ").strip())
                result = scout_app.invoke(Cmd(resume=choice), thread)

            else:
                print(f"[Scout HITL] Unknown interrupt type '{itype}' — skipping.")
                result = scout_app.invoke(Cmd(resume=None), thread)

        payload = result.get("payload", {})
        return {
            "restaurant": payload.get("selected_restaurant", {}),
            "deal": payload.get("selected_deal", {}),
            "payload": payload,
        }

    except Exception as exc:
        print(f"[Scout] Error: {exc}")
        # TODO: replace with real scout_agent import when available as standalone module
        return {
            "restaurant": {},
            "deal": {},
            "payload": {},
        }


def food_agent(
    dish_name: str = None,
    calorie_constraint: str = None,
    payload: dict = None,
) -> dict:
    """
    TODO: wire to the real agent2_food module when it exists as a standalone package.

    Currently delegates to RAG functions directly:
      - dish_name        → query_rag  (Mode B: food inquiry)
      - calorie_constraint → find_dishes_by_calorie_constraint  (Mode C)
      - payload          → calculate_order_calories  (Mode A enrich)

    Returns: { "dishes": [...], "calories": "...", "ingredients": [...], "answer": "..." }
    """
    if dish_name is not None:
        answer = query_rag(
            query=dish_name,
            vectorstore=_vectorstore,
            llm=_llm_rag,
            all_dishes=_all_dishes,
            json_path=_RAG_JSON,
        )
        return {"dishes": [dish_name], "calories": "", "ingredients": [], "answer": answer}

    if calorie_constraint is not None:
        try:
            limit = float(re.search(r"\d+(?:\.\d+)?", calorie_constraint).group())
        except (AttributeError, ValueError):
            limit = 500.0
        matches = find_dishes_by_calorie_constraint(limit, _all_dishes)
        return {"dishes": matches, "calories": calorie_constraint, "ingredients": [], "limit": limit}

    if payload is not None:
        deal = payload.get("selected_deal", {})
        # Use the user's chosen quantity (and portion if given) — not portion alone.
        qty = deal.get("quantity", 1) or 1
        portion = deal.get("portion", "")
        order_qty = f"{qty} × {portion}".strip(" ×") if portion else f"{qty} serving"
        order = [{"name": deal.get("item_name", ""), "quantity": order_qty}]
        results = calculate_order_calories(
            order=order,
            vectorstore=_vectorstore,
            llm=_llm_rag,
            all_dishes=_all_dishes,
            json_path=_RAG_JSON,
        )
        if results:
            r = results[0]
            return {
                "dishes": [r.get("name", "")],
                "calories": str(r.get("calories_per_meal", "")),
                "ingredients": [],
                "answer": (
                    f"{r['name']}: {r.get('calories_per_meal', 'N/A')} kcal "
                    f"({r.get('quantity_grams', '?')}g serving)"
                    if r.get("found") else f"Calorie data not found for {r.get('name', '')}."
                ),
            }
        return {"dishes": [], "calories": "", "ingredients": [], "answer": "No calorie data available."}

    return {"dishes": [], "calories": "", "ingredients": [], "answer": ""}


def order_agent(payload: dict, rag_enrichment: dict | None = None) -> dict:
    """
    Drives the order_finalizer LangGraph and returns a summary dict.

    Passes `rag_enrichment` as a SEPARATE key (the finalizer reads it from the
    top level to include calories in the receipt), not buried inside payload.

    Returns: { "summary", "promo_applied", "final_price", "verified_promo" }
    """
    try:
        from order_finalizer.graph import build_graph as build_order_graph

        print("\n[Order] Running order finalizer…")
        order_app = build_order_graph()
        final_state = order_app.invoke({
            "payload": payload,
            "rag_enrichment": rag_enrichment or {},
        })

        promo = final_state.get("verified_promo")
        return {
            "summary": final_state.get("receipt_summary", ""),
            "promo_applied": bool(promo),
            "final_price": str(final_state.get("final_price", "0")),
            "verified_promo": promo,
        }
    except Exception as exc:
        print(f"[Order] Error: {exc}")
        return {"summary": "", "promo_applied": False, "final_price": "0", "verified_promo": None}


# ═══════════════════════════════════════════════════════════════════════════
# CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════

_CLASSIFY_PROMPT = ChatPromptTemplate.from_template("""
You are a routing classifier for an Egyptian food assistant called Food Pilot.
The user usually writes in Egyptian Arabic.

Classify the user message into exactly one of these modes:
  A — The user wants to ORDER food from a restaurant (e.g. "عايز برجر", "نفسي في بيتزا").
  B — The user is ASKING about a dish (calories, ingredients, description) and does NOT
      want to order now (e.g. "كام سعرة في الكشري؟", "مكونات الملوخية إيه؟").
  C — The user wants food under a CALORIE limit AND to order (e.g. "أكل صحي تحت ٤٠٠ سعرة").
  UNCLEAR — Not enough information; one short clarifying question is needed.

Extract:
  what  — the dish / food entity / calorie description, in the user's own language
          (e.g. "بيتزا", "كشري", "تحت ٤٠٠ سعرة").
  where — the location text if mentioned, else empty string.

Respond with EXACTLY this JSON (no extra text). The "clarification" MUST be in
Egyptian Arabic:
{{
  "mode": "<A|B|C|UNCLEAR>",
  "what":  "<food entity or calorie description>",
  "where": "<location or empty string>",
  "clarification": "<سؤال واحد بالعربي المصري لو الوضع UNCLEAR، وإلا سيبه فاضي>"
}}

User message: {message}
""")


def _classify(message: str) -> dict:
    chain = _CLASSIFY_PROMPT | _llm | StrOutputParser()
    raw = chain.invoke({"message": message}).strip()
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        # Use json.loads (NOT eval) — safe and handles true/false/null correctly.
        return json.loads(match.group()) if match else {}
    except Exception:
        return {
            "mode": "UNCLEAR",
            "what": "",
            "where": "",
            "clarification": "ممكن توضّحلي أكتر إنت عايز إيه؟ (تطلب أكل، تسأل عن طبق، ولا أكل بسعرات معيّنة؟)",
        }


# ═══════════════════════════════════════════════════════════════════════════
# REUSABLE HELPERS (used by the FastAPI bridge — no stdin/graph required)
# ═══════════════════════════════════════════════════════════════════════════

def classify_message(message: str) -> dict:
    """Public classifier: returns {mode, what, where, clarification}."""
    result = _classify(message)
    result.setdefault("mode", "UNCLEAR")
    result.setdefault("what", "")
    result.setdefault("where", "")
    result.setdefault("clarification", "")
    return result


def answer_food_question(question: str) -> str:
    """Mode B: answer a dish question from RAG, in Egyptian Arabic."""
    return query_rag(
        query=question,
        vectorstore=_vectorstore,
        llm=_llm_rag,
        all_dishes=_all_dishes,
        json_path=_RAG_JSON,
    )


def dishes_under_calories(constraint: str) -> tuple[list[str], float]:
    """Mode C step 1: return (dish_names, limit) at/under the calorie limit."""
    try:
        limit = float(re.search(r"\d+(?:\.\d+)?", constraint).group())
    except (AttributeError, ValueError):
        limit = 500.0
    matches = find_dishes_by_calorie_constraint(limit, _all_dishes, _RAG_JSON)
    return matches, limit


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH NODES
# ═══════════════════════════════════════════════════════════════════════════

def node_classify(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── classify ──")
    result = _classify(state["user_message"])
    mode = result.get("mode", "UNCLEAR")
    print(f"[Orchestrator] Mode={mode}  what='{result.get('what','')}' where='{result.get('where','')}'")
    return {
        "mode": mode,
        "what": result.get("what", ""),
        "where": result.get("where", ""),
        "clarification_question": result.get("clarification", ""),
    }


def node_clarify(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── clarify ──")
    question = state.get("clarification_question") or "Could you give me more details?"
    answer = interrupt({"type": "clarify", "question": question})
    # merge the clarification answer back into user_message for re-classification
    combined = f"{state['user_message']} — {answer}"
    print(f"[Orchestrator] Clarification received → re-classifying.")
    return {"user_message": combined}


def node_food_inquiry(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── food_inquiry (Mode B) ──")
    result = food_agent(dish_name=state.get("what", state["user_message"]))
    answer = result.get("answer", "")
    print(f"[Orchestrator] RAG answer: {answer[:120]}…")
    return {"rag_answer": answer, "final_output": answer}


def node_calorie_filter(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── calorie_filter (Mode C step 1) ──")
    constraint = state.get("what", "")
    result = food_agent(calorie_constraint=constraint)
    matches = result.get("dishes", [])
    limit = result.get("limit", 500.0)
    print(f"[Orchestrator] Found {len(matches)} dishes under {limit} kcal/serving.")
    if matches:
        print(f"[Orchestrator] Matches: {', '.join(matches[:5])}{'…' if len(matches)>5 else ''}")
    return {"rag_matches": matches, "calorie_limit": limit}


def node_scout(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── scout ──")
    what = state.get("what", state["user_message"])

    # For Mode C, prefer the first RAG match as the search target
    matches = state.get("rag_matches", [])
    if matches:
        what = matches[0]
        print(f"[Orchestrator] Mode C — using top calorie match: '{what}'")

    where = state.get("where", "Cairo")
    result = scout_agent(what=what, where=where, state=dict(state))
    print(f"[Orchestrator] Scout complete. Restaurant: {result.get('restaurant', {}).get('name', 'N/A')}")
    return {"scout_payload": result.get("payload", {})}


def node_enrich(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── enrich (Mode A step 2) ──")
    payload = state.get("scout_payload", {})
    result = food_agent(payload=payload)
    print(f"[Orchestrator] Enrichment: {result.get('answer', '')[:120]}")
    return {
        "enriched_result": result,
        # attach enrichment to payload so order_finalizer can include it in the receipt
        "scout_payload": {**payload, "rag_enrichment": result},
    }


def node_order(state: OrchestratorState) -> dict:
    print(f"\n[Orchestrator] ── order ──")
    payload = state.get("scout_payload", {})
    # Forward RAG enrichment (Mode A) so the receipt can show calories.
    enrichment = state.get("enriched_result") or payload.get("rag_enrichment") or {}
    result = order_agent(payload=payload, rag_enrichment=enrichment)
    summary = result.get("summary", "")
    final_price = result.get("final_price", "0")
    promo_applied = result.get("promo_applied", False)
    output = summary or (
        f"Order placed!\n"
        f"Promo applied: {promo_applied}\n"
        f"Final price: {final_price} EGP"
    )
    print(f"[Orchestrator] Order complete. Final price: {final_price} EGP")
    return {"order_result": result, "final_output": output}


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════

def _route_after_classify(state: OrchestratorState) -> str:
    mode = state.get("mode", "UNCLEAR")
    if mode == "A":
        return "scout"
    if mode == "B":
        return "food_inquiry"
    if mode == "C":
        return "calorie_filter"
    return "clarify"


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def _route_after_scout(state: OrchestratorState) -> str:
    return "order" if state.get("mode") == "C" else "enrich"


def build_orchestrator_graph(checkpointer=None):
    """Returns the compiled orchestrator graph (with correct Mode A/C routing from scout)."""
    g = StateGraph(OrchestratorState)

    g.add_node("classify", node_classify)
    g.add_node("clarify", node_clarify)
    g.add_node("food_inquiry", node_food_inquiry)
    g.add_node("calorie_filter", node_calorie_filter)
    g.add_node("scout", node_scout)
    g.add_node("enrich", node_enrich)
    g.add_node("order", node_order)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", _route_after_classify, {
        "scout": "scout",
        "food_inquiry": "food_inquiry",
        "calorie_filter": "calorie_filter",
        "clarify": "clarify",
    })
    g.add_edge("clarify", "classify")
    g.add_edge("calorie_filter", "scout")
    g.add_conditional_edges("scout", _route_after_scout, {
        "enrich": "enrich",
        "order": "order",
    })
    g.add_edge("enrich", "order")
    g.add_edge("food_inquiry", END)
    g.add_edge("order", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def run_orchestrator(user_message: str) -> str:
    """
    Entry point for testing.  Drives the orchestrator graph to completion,
    handling any HITL clarification interrupts via stdin.

    Returns the final user-facing response string.
    """
    app = build_orchestrator_graph()
    thread = {"configurable": {"thread_id": f"orch-{id(user_message)}"}}

    print(f"\n{'='*60}")
    print(f"[Orchestrator] User: {user_message}")
    print(f"{'='*60}")

    result = app.invoke({"user_message": user_message}, thread)

    # handle clarify interrupts if any
    while "__interrupt__" in result:
        iv = result["__interrupt__"][0].value
        if iv.get("type") == "clarify":
            answer = input(f"\n[Clarify] {iv['question']}\nYour answer: ").strip()
            result = app.invoke(Command(resume=answer), thread)
        else:
            print(f"[Orchestrator] Unexpected interrupt: {iv}")
            break

    output = result.get("final_output", "")
    print(f"\n{'='*60}")
    print(f"[Orchestrator] Final output:\n{output}")
    print(f"{'='*60}\n")
    return output


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Food Pilot Orchestrator")
    parser.add_argument("message", nargs="?", help="User message to process")
    args = parser.parse_args()

    if args.message:
        run_orchestrator(args.message)
    else:
        print("Food Pilot Orchestrator — interactive mode")
        print("Type your message and press Enter. Ctrl+C to quit.\n")
        while True:
            try:
                msg = input("You: ").strip()
                if msg:
                    run_orchestrator(msg)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
