import os
import sys
import importlib.util

# 2. Dynamically load the order_finalizer module (handling the hyphen in the folder name)
folder_path = os.path.join(os.path.dirname(__file__), "order_finalizer")

# We add the root folder to sys.path so that `agent1_scout` can be imported by order_finalizer
sys.path.append(os.path.dirname(__file__))

# We temporarily add order_finalizer to sys.path so python can resolve relative imports
sys.path.insert(0, folder_path)

# Import the graph directly
from graph import build_graph

def run_test_case(name: str, payload: dict):
    print(f"\n{'='*60}\n🚀 RUNNING TEST CASE: {name}\n{'='*60}")
    
    app = build_graph()
    
    # Initialize the state with the mock payload
    initial_state = {
        "payload": payload
    }
    
    print("⏳ Executing Graph... (This might take a few seconds due to Web Search and LLM calls)\n")
    final_state = app.invoke(initial_state)
    
    print("✅ --- Verified Promo ---")
    promo = final_state.get("verified_promo")
    if promo:
        print(f"Code: {promo.get('code')}")
        print(f"Discount: {promo.get('value')} ({promo.get('discount_type')})")
        print(f"Platform: {promo.get('required_platform')}")
    else:
        print("No valid promo found.")
    
    print("\n💰 --- Final Price ---")
    print(f"{final_state.get('final_price', '0')} EGP")
    
    print("\n📝 --- Receipt Summary ---")
    print(final_state.get("receipt_summary", "No receipt generated"))
    print("\n")

if __name__ == "__main__":
    # Test Case 1: Buffalo Burger (Very likely to have active online promos)
    mock_payload_1 = {
        "order_status": "configured",
        "user_intent": "I want a burger",
        "selected_restaurant": {
            "name": "Buffalo Burger",
            "address": "Maadi, Cairo",
            "coordinates": {"lat": 29.9538, "lon": 31.2709},
            "google_maps_rating": 4.5
        },
        "selected_deal": {
            "item_name": "Animal Style Burger Combo",
            "price": "250 EGP",
            "currency": "EGP",
            "deal_description": "Burger + Fries + Drink",
            "source_url": "https://buffaloburger.com",
            "quantity": 1,
            "portion": "Large"
        }
    }
    
    # Test Case 2: A local/generic restaurant (Less likely to have a promo code)
    mock_payload_2 = {
        "order_status": "configured",
        "user_intent": "I want traditional food",
        "selected_restaurant": {
            "name": "Sobhy Kaber",
            "address": "Shoubra, Cairo",
            "coordinates": {"lat": 30.0716, "lon": 31.2465},
            "google_maps_rating": 4.6
        },
        "selected_deal": {
            "item_name": "Mix Grill",
            "price": "400 EGP",
            "currency": "EGP",
            "deal_description": "Kofta, Kebab, Tarb",
            "source_url": "",
            "quantity": 1,
            "portion": "1 KG"
        }
    }

    run_test_case("Known Franchise (Buffalo Burger)", mock_payload_1)
    run_test_case("Local Traditional Restaurant (Sobhy Kaber)", mock_payload_2)
