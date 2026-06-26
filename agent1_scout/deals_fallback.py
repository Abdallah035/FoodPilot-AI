"""Task 8b — Tavily open-web fallback for menu deals.

Used only when the restaurant isn't on Talabat (Task 8a returned []). Searches
the open web (Elmenus, Otlob, blogs, the restaurant's own site) with Tavily,
then uses Azure OpenAI to extract structured `Deal` objects from the result snippets.

Prices found here are less authoritative than Talabat; any item still missing a
price is handled by the LLM estimate step (Task 8c).
"""

from __future__ import annotations

from pydantic import BaseModel

import config
from .state import Deal

# Egyptian food sources worth searching when Talabat has nothing.
_FALLBACK_DOMAINS = ["elmenus.com", "otlob.com", "foursquare.com", "facebook.com"]


class DealList(BaseModel):
    """Structured-output wrapper so the LLM returns a list of deals."""

    deals: list[Deal]


def _tavily_web_results(restaurant_name: str, food_entity: str, max_results: int = 6) -> list[dict]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    queries = [
        f"{restaurant_name} menu prices Egypt {food_entity}".strip(),
        f"{restaurant_name} {food_entity} price EGP".strip(),
    ]
    results: list[dict] = []
    for q in queries:
        resp = client.search(
            query=q,
            max_results=max_results,
            search_depth="advanced",
            include_domains=_FALLBACK_DOMAINS,
            include_answer=False,
        )
        results.extend(resp.get("results", []))
    # de-dup by url
    seen, unique = set(), []
    for r in results:
        u = r.get("url")
        if u and u not in seen:
            seen.add(u)
            unique.append(r)
    return unique


def _extract_deals(results: list[dict], restaurant_name: str, food_entity: str) -> list[Deal]:
    if not results:
        return []

    context = "\n\n---\n\n".join(
        f"URL: {r.get('url','')}\nTitle: {r.get('title','')}\nContent: {r.get('content','')}"
        for r in results
    )

    llm = config.get_azure_openai_llm(temperature=0)
    structured = llm.with_structured_output(DealList)
    prompt = (
        f"From the web results below, extract concrete menu items / deals for the "
        f"restaurant '{restaurant_name}', focused on '{food_entity}'. The text may be "
        f"Arabic or English.\n"
        f"For each: item_name, price (digits only as a string in EGP; leave '' if no "
        f"price is stated), currency 'EGP', deal_description, source_url (the URL it "
        f"came from). Keep quantity=1 and portion=''.\n"
        f"Only include items you find evidence for. If none, return an empty list.\n\n"
        f"=== WEB RESULTS ===\n{context}"
    )
    return structured.invoke(prompt).deals


def tavily_menu_fallback(
    restaurant_name: str,
    food_entity: str = "",
    max_results: int = 6,
) -> list[Deal]:
    """Find menu deals from the open web when Talabat has no page.

    Raises if TAVILY_API_KEY or Azure OpenAI configuration is missing.
    """
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env.")
    config.require_azure_openai()

    results = _tavily_web_results(restaurant_name, food_entity, max_results=max_results)
    return _extract_deals(results, restaurant_name, food_entity)
