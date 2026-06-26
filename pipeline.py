from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from agent1_scout.state import OrderPayload
import config

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RAG_JSON = PROJECT_ROOT / "RAG" / "data.json"
DEFAULT_RAG_PERSIST_DIR = PROJECT_ROOT / "RAG" / "chroma_dishes_db"
RagDependencies = tuple[Any, Any, list[dict[str, Any]]]
RagCalculator = Callable[[list[dict[str, Any]], Any, Any, list[dict[str, Any]] | None, str], list[dict[str, Any]]]


def _as_dict(payload: dict[str, Any] | OrderPayload) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return payload.model_dump()


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _load_rag_dependencies(
    json_path: str | os.PathLike[str] | None = None,
    persist_dir: str | os.PathLike[str] | None = None,
) -> RagDependencies:
    from RAG.Rag import build_rag_pipeline

    config.require_azure_openai()

    path = Path(json_path or DEFAULT_RAG_JSON)
    return build_rag_pipeline(str(path), str(persist_dir or DEFAULT_RAG_PERSIST_DIR))


@lru_cache(maxsize=1)
def _cached_rag_dependencies() -> RagDependencies:
    return _load_rag_dependencies()


def _portion_to_grams(portion: str, quantity: int | float) -> float | None:
    text = portion.lower().strip()
    if not text:
        return None

    if re.search(r"\b(half|1/2)\b|نص|نصف", text):
        return 500.0 * quantity
    if re.search(r"\b(quarter|1/4)\b|ربع", text):
        return 250.0 * quantity

    match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|kilo|kilogram|kilograms|كيلو)", text)
    if match:
        return float(match.group(1)) * 1000.0 * quantity

    match = re.search(r"(\d+(?:\.\d+)?)\s*(g|gram|grams|جرام|غرام)", text)
    if match:
        return float(match.group(1)) * quantity

    return None


def _build_rag_order(payload: dict[str, Any]) -> list[dict[str, Any]]:
    deal = payload.get("selected_deal", {})
    user_intent = _compact_text(payload.get("user_intent"))
    item_name = user_intent or _compact_text(deal.get("item_name"))
    description = _compact_text(deal.get("deal_description"))
    portion = _compact_text(deal.get("portion"))
    quantity = deal.get("quantity", 1) or 1

    try:
        quantity_count = float(quantity)
    except (TypeError, ValueError):
        quantity_count = 1.0

    grams = _portion_to_grams(portion, quantity_count)
    if grams is not None:
        order_quantity: str | float = grams
    elif portion:
        order_quantity = f"{int(quantity_count) if quantity_count.is_integer() else quantity_count} {portion} serving(s)"
    else:
        order_quantity = f"{int(quantity_count) if quantity_count.is_integer() else quantity_count} meal(s)"

    context = " | ".join(part for part in (user_intent, description, portion) if part)
    item = {"name": item_name, "quantity": order_quantity}
    if context:
        item["context"] = context
    return [item]


def _format_rag_answer(payload: dict[str, Any], items: list[dict[str, Any]]) -> str:
    if not items:
        return "Nutrition data was not available for this order."

    deal = payload.get("selected_deal", {})
    description = _compact_text(deal.get("deal_description"))
    lines = []
    for item in items:
        name = _compact_text(item.get("name")) or "Selected item"
        calories = item.get("calories_per_meal")
        grams = item.get("quantity_grams")
        source = item.get("source") or "unknown source"
        if calories is None:
            lines.append(f"{name}: calorie data was not found.")
            continue
        grams_text = f" for about {grams:g}g" if isinstance(grams, (int, float)) else ""
        lines.append(f"{name}: approximately {calories:g} calories{grams_text} ({source}).")

    if description:
        lines.append(f"Deal context: {description}.")

    return " ".join(lines)


def _rag_sources(items: list[dict[str, Any]]) -> list[str]:
    sources = []
    for item in items:
        source = item.get("source")
        if source:
            sources.append(f"{item.get('name', 'item')} ({source})")
    return sources


def _rag_status(items: list[dict[str, Any]]) -> str:
    if items and all(item.get("found") for item in items):
        return "completed"
    return "partial"


def _calculate_rag_calories(
    order: list[dict[str, Any]],
    vectorstore: Any,
    llm: Any,
    all_dishes: list[dict[str, Any]] | None,
    json_path: str,
) -> list[dict[str, Any]]:
    from RAG.Rag import calculate_order_calories

    return calculate_order_calories(order, vectorstore, llm, all_dishes=all_dishes, json_path=json_path)


def enrich_payload_with_rag(
    payload: dict[str, Any] | OrderPayload,
    *,
    rag_dependencies: RagDependencies | None = None,
    rag_calculator: RagCalculator | None = None,
    json_path: str | os.PathLike[str] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Add Agent 2/RAG nutrition context without changing Scout's payload contract."""
    payload_dict = _as_dict(payload)
    if not enabled:
        return {
            "payload": payload_dict,
            "rag_enrichment": {
                "status": "skipped",
                "answer": "",
                "sources": [],
                "items": [],
            },
        }

    try:
        deps = rag_dependencies or _cached_rag_dependencies()
        vectorstore, llm, all_dishes = deps
        calculator = rag_calculator or _calculate_rag_calories
        items = calculator(
            _build_rag_order(payload_dict),
            vectorstore,
            llm,
            all_dishes,
            str(json_path or DEFAULT_RAG_JSON),
        )
        answer = _format_rag_answer(payload_dict, items)
        sources = _rag_sources(items)
        status = _rag_status(items)
        error = ""
    except Exception as exc:
        answer = ""
        sources = []
        items = []
        status = "failed"
        error = str(exc)

    enrichment = {
        "status": status,
        "answer": answer,
        "sources": sources,
        "items": items,
    }
    if error:
        enrichment["error"] = error

    return {
        "payload": payload_dict,
        "rag_enrichment": enrichment,
    }


def finalize_order(
    payload: dict[str, Any] | OrderPayload,
    *,
    rag_enrichment: dict[str, Any] | None = None,
    finalizer_app: Any | None = None,
) -> dict[str, Any]:
    """Pass Scout/RAG output to the order finalizer and return its final state."""
    payload_dict = _as_dict(payload)
    if finalizer_app is None:
        from order_finalizer.graph import build_graph as build_finalizer_graph

        finalizer_app = build_finalizer_graph()
    return finalizer_app.invoke({
        "payload": payload_dict,
        "rag_enrichment": rag_enrichment or {},
    })


def run_post_scout_pipeline(
    payload: dict[str, Any] | OrderPayload,
    *,
    rag_dependencies: RagDependencies | None = None,
    rag_calculator: RagCalculator | None = None,
    rag_json_path: str | os.PathLike[str] | None = None,
    rag_enabled: bool = True,
    finalizer_app: Any | None = None,
) -> dict[str, Any]:
    """Run Agent 2/RAG enrichment, then Agent 3/order finalization."""
    enriched = enrich_payload_with_rag(
        payload,
        rag_dependencies=rag_dependencies,
        rag_calculator=rag_calculator,
        json_path=rag_json_path,
        enabled=rag_enabled,
    )
    finalizer_state = finalize_order(
        enriched["payload"],
        rag_enrichment=enriched["rag_enrichment"],
        finalizer_app=finalizer_app,
    )
    return {
        "payload": enriched["payload"],
        "rag_enrichment": enriched["rag_enrichment"],
        "finalizer": finalizer_state,
        "receipt_summary": finalizer_state.get("receipt_summary", ""),
        "final_price": finalizer_state.get("final_price"),
        "verified_promo": finalizer_state.get("verified_promo"),
    }


def print_pipeline_result(result: dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("FINAL INTEGRATED RESULT")
    print("=" * 60)

    finalizer = result.get("finalizer", {})
    receipt = result.get("receipt_summary") or finalizer.get("receipt_summary")
    if receipt:
        print("\nReceipt:")
        print(receipt)

    final_price = result.get("final_price")
    if final_price is not None:
        print(f"\nFinal price: {final_price:.2f} EGP")

    promo = result.get("verified_promo")
    if promo:
        print("\nVerified promo:")
        print(json.dumps(promo, ensure_ascii=False, indent=2))

    rag = result.get("rag_enrichment", {})
    print("\nRAG enrichment:")
    print(json.dumps(rag, ensure_ascii=False, indent=2))
