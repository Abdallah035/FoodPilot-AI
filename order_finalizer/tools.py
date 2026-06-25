from typing import List
from tavily import TavilyClient

from .config import TAVILY_API_KEY

def search_promos(restaurant_name: str) -> str:
    """Uses Tavily to search for live promo codes for the restaurant."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is not set.")
        
    client = TavilyClient(api_key=TAVILY_API_KEY)
    
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
