from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from agent1_scout.state import OrderPayload

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_RAG_JSON = PROJECT_ROOT / "RAG" / "data.json"
DEFAULT_RAG_PERSIST_DIR = PROJECT_ROOT / "RAG" / "chroma_dishes_db"
RagDependencies = tuple[Any, Any, Any, Any, list[dict[str, Any]]]
RagQuery = Callable[[str, Any, Any, Any, Any, list[dict[str, Any]]], tuple[str, list[str]]]


def _as_dict(payload: dict[str, Any] | OrderPayload) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return payload.model_dump()


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _load_rag_dependencies(json_path: str | os.PathLike[str] | None = None) -> RagDependencies:
    from RAG.Rag import build_rag_pipeline

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is required for RAG enrichment.")

    path = Path(json_path or DEFAULT_RAG_JSON)
    return build_rag_pipeline(str(path), api_key, str(DEFAULT_RAG_PERSIST_DIR))


@lru_cache(maxsize=1)
def _cached_rag_dependencies() -> RagDependencies:
    return _load_rag_dependencies()


def _build_rag_question(payload: dict[str, Any]) -> str:
    deal = payload.get("selected_deal", {})
    item_name = _compact_text(deal.get("item_name"))
    description = _compact_text(deal.get("deal_description"))
    portion = _compact_text(deal.get("portion"))

    parts = [item_name]
    if description:
        parts.append(description)
    if portion:
        parts.append(f"portion: {portion}")

    dish = " - ".join(part for part in parts if part)
    return (
        "Find nutrition and ingredient information for this ordered dish. "
        "Return calories, key ingredients, and any relevant notes. "
        f"Dish: {dish}"
    )


def enrich_payload_with_rag(
    payload: dict[str, Any] | OrderPayload,
    *,
    rag_dependencies: RagDependencies | None = None,
    rag_query: RagQuery | None = None,
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
            },
        }

    try:
        deps = rag_dependencies or _cached_rag_dependencies()
        if rag_query is None:
            from RAG.Rag import query_rag as rag_query

        retriever, vectorstore, llm, prompt, all_dishes = deps
        answer, sources = rag_query(
            _build_rag_question(payload_dict),
            retriever,
            vectorstore,
            llm,
            prompt,
            all_dishes,
        )
        status = "completed"
        error = ""
    except Exception as exc:
        answer = ""
        sources = []
        status = "failed"
        error = str(exc)

    enrichment = {
        "status": status,
        "answer": answer,
        "sources": sources,
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
    rag_query: RagQuery | None = None,
    rag_enabled: bool = True,
    finalizer_app: Any | None = None,
) -> dict[str, Any]:
    """Run Agent 2/RAG enrichment, then Agent 3/order finalization."""
    enriched = enrich_payload_with_rag(
        payload,
        rag_dependencies=rag_dependencies,
        rag_query=rag_query,
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