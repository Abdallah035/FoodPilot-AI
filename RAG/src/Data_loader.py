import json

with open("Egyptian_Dishes_Complete_Reference.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

recipes = raw_data["recipes"]
print(f"Loaded {len(recipes)} recipes")

