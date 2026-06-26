"""Task 8c — LLM price estimate for deals missing a price.

Some fallback (open-web) deals arrive without a price. Rather than drop them, we
ask Groq for a typical current EGP price and CLEARLY flag it as estimated by
appending "(estimated price)" to the deal_description. Deals that already have a
real price are returned unchanged.

(We keep the Deal schema unchanged — no extra field — so the estimate is marked
in the human-readable description.)
"""

from __future__ import annotations

from . import config
from .state import Deal

ESTIMATE_NOTE = "(estimated price)"


def _needs_price(d: Deal) -> bool:
    try:
        return not (d.price and float(d.price) > 0)
    except (TypeError, ValueError):
        return True


def _estimate_one(item_name: str, restaurant_name: str) -> str:
    """Ask Groq for a plain numeric price. Returns digits, or "" on failure.

    We deliberately avoid `with_structured_output` here: forcing a tool call for
    a one-number answer makes Groq intermittently 400 with
    "Tool choice is required, but model did not call a tool". A plain text reply
    that we parse for digits is more robust for such a trivial output.
    """
    from langchain_groq import ChatGroq

    llm = ChatGroq(model=config.GROQ_MODEL, temperature=0, api_key=config.GROQ_API_KEY)
    prompt = (
        "Estimate a typical current price in Egyptian Pounds (EGP) for this menu "
        f"item at a normal Egyptian restaurant.\n"
        f"Restaurant: {restaurant_name}\nItem: {item_name}\n"
        "Reply with the number only — digits, no currency word, no explanation."
    )
    try:
        resp = llm.invoke(prompt)
    except Exception:
        return ""
    text = resp.content if hasattr(resp, "content") else str(resp)
    # keep only the first run of digits
    digits = ""
    for ch in str(text):
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return digits


def estimate_missing_prices(deals: list[Deal], restaurant_name: str) -> list[Deal]:
    """Fill missing prices with a flagged LLM estimate; leave real prices as-is."""
    if not deals:
        return deals
    if not config.has_groq():
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env.")

    out: list[Deal] = []
    for d in deals:
        if not _needs_price(d):
            out.append(d)
            continue
        price = _estimate_one(d.item_name, restaurant_name)
        if not price:
            # Couldn't estimate — keep the deal unchanged rather than crash.
            out.append(d)
            continue
        desc = d.deal_description.strip()
        flagged = f"{desc} {ESTIMATE_NOTE}".strip() if desc else ESTIMATE_NOTE
        out.append(d.model_copy(update={"price": price, "deal_description": flagged}))
    return out
