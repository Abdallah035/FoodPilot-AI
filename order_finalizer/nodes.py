from __future__ import annotations
import json
import re

from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .state import FinalizerState, VerifiedPromo
from .tools import search_promos
from .config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_VERSION
)

def get_llm():
    if not AZURE_OPENAI_API_KEY:
        raise EnvironmentError("AZURE_OPENAI_API_KEY is not set.")
    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        openai_api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=0.0
    )

def search_promos_node(state: FinalizerState) -> dict:
    # Handle both dict and BaseModel depending on how it's passed
    payload = state["payload"]
    restaurant_name = payload["selected_restaurant"]["name"] if isinstance(payload, dict) else payload.selected_restaurant.name
    raw_results = search_promos(restaurant_name)
    return {"raw_search_results": raw_results}

def verify_promo_node(state: FinalizerState) -> dict:
    llm = get_llm()
    payload = state["payload"]
    deal = payload["selected_deal"] if isinstance(payload, dict) else payload.selected_deal
    restaurant_name = payload["selected_restaurant"]["name"] if isinstance(payload, dict) else payload.selected_restaurant.name
    item_name = deal["item_name"] if isinstance(deal, dict) else deal.item_name
    
    raw_results = state.get("raw_search_results", "")
    
    prompt = ChatPromptTemplate.from_template("""
You are a strict promo code verification judge.

Restaurant: {restaurant_name}
Deal/Items: {deal_item}

Here are some raw search results for promo codes:
{raw_results}

Your job is to find ONE valid promo code or active voucher/offer that applies to the deal. 
Rules:
1. It must not be expired.
2. It must EXPLICITLY mention the restaurant "{restaurant_name}" in the same context as the promo code or offer. Do NOT hallucinate or apply a generic code (like for Noon or Carrefour) to this restaurant.
3. It must apply to the items ordered.
4. Identify the required platform (e.g., Waffarha, Talabat, Elmenus, Direct).

If you find a valid promo or offer, return a JSON object exactly like this:
{{
    "code": "CODE10",
    "discount_type": "percentage",
    "value": 10.0,
    "required_platform": "Talabat"
}}
Note: "discount_type" must be either "percentage" or "flat".

If no valid promo is found, return exactly:
{{}}

Return ONLY valid JSON.
""")
    chain = prompt | llm | StrOutputParser()
    res = chain.invoke({
        "restaurant_name": restaurant_name,
        "deal_item": item_name,
        "raw_results": raw_results
    })
    
    verified_promo = None
    try:
        # Extract json part if wrapped in backticks
        match = re.search(r'\{.*\}', res, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            if "code" in parsed and "value" in parsed:
                verified_promo = parsed
    except Exception:
        pass
        
    return {"verified_promo": verified_promo}

def calculate_price_node(state: FinalizerState) -> dict:
    payload = state["payload"]
    deal = payload["selected_deal"] if isinstance(payload, dict) else payload.selected_deal
    price_str = deal.get("price", "0") if isinstance(deal, dict) else (deal.price or "0")
    quantity = deal.get("quantity", 1) if isinstance(deal, dict) else (deal.quantity or 1)
    
    # extract numeric value from price_str (e.g. "150 EGP")
    match = re.search(r'([\d\.]+)', price_str)
    unit_price = float(match.group(1)) if match else 0.0
    base_price = unit_price * quantity
    
    final_price = base_price
    promo = state.get("verified_promo")
    
    if promo:
        val = float(promo["value"])
        if promo["discount_type"] == "percentage":
            final_price = base_price * (1 - val/100.0)
        elif promo["discount_type"] == "flat":
            final_price = max(0.0, base_price - val)
            
    return {"final_price": final_price}

def generate_receipt_node(state: FinalizerState) -> dict:
    llm = get_llm()
    payload = state["payload"]
    deal = payload["selected_deal"] if isinstance(payload, dict) else payload.selected_deal
    restaurant = payload["selected_restaurant"] if isinstance(payload, dict) else payload.selected_restaurant
    
    restaurant_name = restaurant["name"] if isinstance(restaurant, dict) else restaurant.name
    item_name = deal["item_name"] if isinstance(deal, dict) else deal.item_name
    quantity = deal.get("quantity", 1) if isinstance(deal, dict) else (deal.quantity or 1)
    original_price = deal.get("price", "0 EGP") if isinstance(deal, dict) else deal.price
    
    if int(quantity) > 1:
        item_name = f"{quantity}x {item_name}"
    
    promo = state.get("verified_promo")
    final_price = state.get("final_price", 0.0)
    rag_enrichment = state.get("rag_enrichment") or {}
    nutrition_context = rag_enrichment.get("answer") or "Not available"
    
    prompt = ChatPromptTemplate.from_template("""
You are a helpful customer service assistant for Food Pilot.
Generate a friendly markdown receipt for the user.

Restaurant: {restaurant_name}
(Contact info will be provided here soon)

Item Ordered: {item_name}
Original Price: {original_price}

Applied Promo: {promo_details}

Nutrition Context from RAG: {nutrition_context}

Final Price: {final_price} EGP

Format this nicely using Markdown. If there is a promo, explicitly tell the user which platform to use it on.
""")
    
    promo_details = "None"
    if promo:
        promo_details = f"Code '{promo['code']}' (-{promo['value']} {promo['discount_type']}) on {promo['required_platform']}"
        
    chain = prompt | llm | StrOutputParser()
    receipt = chain.invoke({
        "restaurant_name": restaurant_name,
        "item_name": item_name,
        "original_price": original_price,
        "promo_details": promo_details,
        "nutrition_context": nutrition_context,
        "final_price": f"{final_price:.2f}"
    })
    
    return {"receipt_summary": receipt}
