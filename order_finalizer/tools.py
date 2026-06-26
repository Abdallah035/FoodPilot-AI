from typing import List
from tavily import TavilyClient

import config

def search_promos(restaurant_name: str) -> str:
    """Uses Tavily to search for live promo codes for the restaurant."""
    if not config.TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is not set.")
        
    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    
    # Execute a focused search
    query = f"{restaurant_name} restaurant (promo code OR discount OR offer) Egypt 2026 Waffarha Talabat Elmenus"
    response = client.search(
        query=query, 
        search_depth="advanced",
        max_results=5
    )
    
    # Combine results into a text block
    results_text = []
    for result in response.get("results", []):
        results_text.append(f"Source: {result.get('url')}\nContent: {result.get('content')}")
        
    return "\n\n".join(results_text)
