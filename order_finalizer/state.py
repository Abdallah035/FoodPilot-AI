from __future__ import annotations
from typing import Any, TypedDict, Optional, List
from agent1_scout.state import OrderPayload

class VerifiedPromo(TypedDict):
    code: str
    discount_type: str  # "percentage" or "flat"
    value: float
    required_platform: str  # e.g., "Talabat", "Elmenus", "Direct"

class FinalizerState(TypedDict, total=False):
    payload: OrderPayload
    search_queries: List[str]
    raw_search_results: str
    verified_promo: Optional[VerifiedPromo]
    final_price: float
    receipt_summary: str
    rag_enrichment: dict[str, Any]
