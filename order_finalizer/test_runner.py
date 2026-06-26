import os
import sys
import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Add the root folder to sys.path
root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(root_dir)

# Create a dummy package to trick Python's relative import system
pkg = types.ModuleType("order_finalizer")
pkg.__path__ = [os.path.dirname(__file__)]
pkg.__package__ = "order_finalizer"
sys.modules["order_finalizer"] = pkg

# Now we can import the module as if the folder was named order_finalizer
from order_finalizer.graph import build_graph

def run_test_case(name: str, payload: dict):
    print(f"\n{'='*60}\n RUNNING TEST CASE: {name}\n{'='*60}")
    
    app = build_graph()
    initial_state = {"payload": payload}
    
    print(" Executing Graph... (This might take a few seconds)\n")
    final_state = app.invoke(initial_state)
    
    print(" --- Verified Promo ---")
    promo = final_state.get("verified_promo")
    if promo:
        print(f"Code: {promo.get('code')}")
        print(f"Discount: {promo.get('value')} ({promo.get('discount_type')})")
        print(f"Platform: {promo.get('required_platform')}")
    else:
        print("No valid promo found.")
    
    print("\n --- Final Price ---")
    print(f"{final_state.get('final_price', '0')} EGP")
    
    print("\n --- Receipt Summary ---")
    print(final_state.get("receipt_summary", "No receipt generated"))
    print("\n")

if __name__ == "__main__":
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
    
    mock_payload_3 = {
        "order_status": "configured",
        "user_intent": "I want 3 pizzas for a party",
        "selected_restaurant": {
            "name": "Papa Johns",
            "address": "New Cairo",
            "coordinates": {"lat": 30.0216, "lon": 31.4465},
            "google_maps_rating": 4.4
        },
        "selected_deal": {
            "item_name": "Super Papa's Pizza",
            "price": "220 EGP",
            "currency": "EGP",
            "deal_description": "Pepperoni, Italian sausage, onions, green peppers",
            "source_url": "https://papajohns.eg",
            "quantity": 3,
            "portion": "Large"
        }
    }

    mock_payload_4 = {
        "order_status": "configured",
        "user_intent": "I want 4 fried chicken meals",
        "selected_restaurant": {
            "name": "KFC",
            "address": "Zamalek, Cairo",
            "coordinates": {"lat": 30.0616, "lon": 31.2265},
            "google_maps_rating": 4.1
        },
        "selected_deal": {
            "item_name": "Mighty Zinger Combo",
            "price": "300 EGP",
            "currency": "EGP",
            "deal_description": "Mighty zinger sandwich, fries, and drink",
            "source_url": "https://egypt.kfc.me",
            "quantity": 4,
            "portion": "Large"
        }
    }

    mock_payload_5 = {
        "order_status": "configured",
        "user_intent": "I want to order koshari",
        "selected_restaurant": {
            "name": "Koshari Eltahrir",
            "address": "Dokki, Cairo",
            "coordinates": {"lat": 30.0382, "lon": 31.2113},
            "google_maps_rating": 4.3
        },
        "selected_deal": {
            "item_name": "Mega Koshari Box",
            "price": "60 EGP",
            "currency": "EGP",
            "deal_description": "Large koshari box with extra toppings",
            "source_url": "https://kosharyeltahrir.com",
            "quantity": 2,
            "portion": "Mega"
        }
    }

    mock_payload_6 = {
        "order_status": "configured",
        "user_intent": "I want to order from Beremer",
        "selected_restaurant": {
            "name": "Beremer",
            "address": "Cairo, Egypt",
            "coordinates": {"lat": 30.0444, "lon": 31.2357},
            "google_maps_rating": 4.5
        },
        "selected_deal": {
            "item_name": "Signature Dish",
            "price": "250 EGP",
            "currency": "EGP",
            "deal_description": "Chef's special",
            "source_url": "",
            "quantity": 1,
            "portion": "Regular"
        }
    }

    # run_test_case("Known Franchise (Buffalo Burger)", mock_payload_1)
    # run_test_case("Local Traditional Restaurant (Sobhy Kaber)", mock_payload_2)
    # run_test_case("Multi-Item Order (3x Papa Johns Pizzas)", mock_payload_3)
    # run_test_case("Multi-Item Order (4x KFC Meals)", mock_payload_4)
    # run_test_case("Waffarha Promo Test (2x Koshari Eltahrir)", mock_payload_5)
    # run_test_case("Beremer Order", mock_payload_6)
