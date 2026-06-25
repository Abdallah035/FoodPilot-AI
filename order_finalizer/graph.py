from langgraph.graph import StateGraph, START, END
from .state import FinalizerState
from .nodes import (
    search_promos_node,
    verify_promo_node,
    calculate_price_node,
    generate_receipt_node
)

def build_graph():
    builder = StateGraph(FinalizerState)
    
    builder.add_node("search_promos", search_promos_node)
    builder.add_node("verify_promo", verify_promo_node)
    builder.add_node("calculate_price", calculate_price_node)
    builder.add_node("generate_receipt", generate_receipt_node)
    
    builder.add_edge(START, "search_promos")
    builder.add_edge("search_promos", "verify_promo")
    builder.add_edge("verify_promo", "calculate_price")
    builder.add_edge("calculate_price", "generate_receipt")
    builder.add_edge("generate_receipt", END)
    
    return builder.compile()
