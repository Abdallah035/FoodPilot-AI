import os
import json
from dotenv import load_dotenv

# Load environment variables before importing our modules
load_dotenv()

from agent1_scout.deals import find_deals

def run_manual_test():
    print("=" * 60)
    print("FOOD PILOT — AGENT 1 DEALS TESTER")
    print("=" * 60)
    
    # Quick environment check
    if not os.getenv("TAVILY_API_KEY"):
        print("❌ Error: TAVILY_API_KEY is missing from your environment/dotenv.")
        return
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY is missing from your environment/dotenv.")
        return

    # Prompt user for manual testing input
    restaurant = input("Enter restaurant name (e.g., Buffalo Burger, Kansas Fried Chicken): ").strip()
    if not restaurant:
        print("Restaurant name cannot be empty. Defaulting to 'Buffalo Burger'.")
        restaurant = "Buffalo Burger"
        
    location = input("Enter location / area (e.g., Maadi, Alexandria) [Optional]: ").strip()

    print(f"\n🚀 Running discovery deep-dive for: '{restaurant}' in '{location or 'Anywhere'}'...")
    print("-" * 60)
    
    try:
        deals = find_deals(restaurant_name=restaurant, location=location, max_results=5)
        
        if not deals:
            print("\n⚠️ No deals or menu items were found. Check the debug logs above.")
            return
            
        print(f"\n✅ Found {len(deals)} items successfully!")
        print("-" * 60)
        
        for i, deal in enumerate(deals, start=1):
            print(f"[{i}] {deal.item_name}")
            print(f"    💰 Price: {deal.price} {deal.currency}")
            if deal.deal_description:
                print(f"    📝 Details: {deal.deal_description}")
            print(f"    🔗 Source: {deal.source_url}")
            print("-" * 40)
            
        # Optional: dump raw JSON serialization to verify alignment with schema
        print("\n📋 Serialized JSON State Preview:")
        preview_list = [d.model_dump() for d in deals]
        print(json.dumps(preview_list, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ Test crashed with an unhandled exception: {e}")

if __name__ == "__main__":
    run_manual_test()