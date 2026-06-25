"""Task 8 — Tavily deal deep-dive with aggregator targeting.

Instead of broad web searches, we force Tavily to search explicitly on 
delivery aggregators (Elmenus, Talabat) where prices are structured and guaranteed.
We use Tavily's "advanced" extraction to handle JavaScript-rendered menus,
and Pydantic/Groq to parse the Markdown into clean JSON.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from tavily import TavilyClient

from . import config
from .state import Deal

class DealList(BaseModel):
    deals: list[Deal] = Field(
        description="A list of menu items and their prices extracted from the text."
    )

_SYSTEM_PROMPT = """You are a precise data extraction assistant.
You are given markdown text extracted from a restaurant delivery website (like Elmenus or Talabat).
Extract the menu items, combos, and their prices.

Rules:
- Ignore out-of-stock items or empty categories.
- Clean up the item names.
- Price must be just the number (no currency symbols or text).
- Default currency is "EGP".
- Include descriptions or portion sizes in 'deal_description' if available.
- YOU MUST RETURN VALID JSON matching the schema.
"""

def find_deals(
    restaurant_name: str,
    location: str = "",
    max_results: int = 10,
) -> list[Deal]:
    """Search for menu items targeting reliable delivery platforms."""
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not set")
    if not config.has_groq():
        raise RuntimeError("GROQ_API_KEY not set")

    tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    llm = ChatGroq(model=config.GROQ_MODEL, temperature=0, api_key=config.GROQ_API_KEY)

    # 1. Targeted Search Strategy
    queries = [
        f'"{restaurant_name}" {location} site:menumisr.com',
        f'"{restaurant_name}" menu prices {location}' 
    ]

    search_res = None
    for q in queries:
        try:
            print(f"DEBUG: Searching Tavily with -> '{q}'")
            res = tavily_client.search(q, max_results=2, search_depth="advanced")
            if res.get("results"):
                search_res = res
                break
        except Exception as e:
            print(f"DEBUG: Search failed for '{q}': {e}")
            continue

    if not search_res or not search_res.get("results"):
        print("DEBUG: No menu sources found.")
        return []

    best_url = search_res["results"][0]["url"]
    print(f"DEBUG: Extracting content from: {best_url}")

    # 2. Advanced Content Extraction
    try:
        # Use advanced depth to render JavaScript and grab dynamic menus
        extract_res = tavily_client.extract([best_url], extract_depth="advanced")
        result_data = extract_res.get("results", [])[0]
        
        # Prioritize the cleaned Markdown 'content' over raw HTML 'raw_content'
        full_text = result_data.get("content") or result_data.get("raw_content", "")
        
        # Markdown is highly compressed compared to HTML, 40k chars is plenty for a full menu
        if len(full_text) > 40000:
            full_text = full_text[:40000]
            
    except Exception as e:
        print(f"DEBUG: Tavily extraction failed: {e}")
        return []

    if not full_text.strip():
        print("DEBUG: Extracted content was empty.")
        return []

    # 3. Structured LLM Parsing
    print(f"DEBUG: Handing off {len(full_text)} chars of markdown to Groq...")
    try:
        # FIX: Force json_mode to bypass the LangChain tool-naming bug
        structured_llm = llm.with_structured_output(DealList, method="json_mode")
        response: DealList = structured_llm.invoke([
            ("system", _SYSTEM_PROMPT),
            ("human", f"Restaurant: {restaurant_name}\nWebsite Text:\n{full_text}")
        ])
        
        final_deals = []
        for deal in response.deals[:max_results]:
            deal.source_url = best_url
            final_deals.append(deal)
            
        print(f"DEBUG: Successfully extracted {len(final_deals)} deals.")
        return final_deals

    except Exception as e:
        print(f"DEBUG: Groq extraction failed: {e}")
        return []