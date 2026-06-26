import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import config

from Rag import (
    build_rag_pipeline,
    calculate_order_calories,
)

config.require_azure_openai()

JSON_PATH   = "data.json"
PERSIST_DIR = "./chroma_dishes_db"

print("Building RAG pipeline...")
vectorstore, llm, all_dishes = build_rag_pipeline(
    JSON_PATH, PERSIST_DIR
)
print(f"Pipeline ready — {len(all_dishes)} dishes indexed.\n")

# ── Test order ────────────────────────────────────────────────────────────────
order = [
    {"name": "حواوشي",         "quantity": "رغيف"},           # one hawawshi loaf
    {"name": "كشري",           "quantity": "طبق"},            # a plate of koshari
    {"name": "فول مدمس",       "quantity": "ربع كيلو"},        # 250g
    {"name": "طعمية / فلافل مصرية", "quantity": "5 حبات"},   # 5 pieces
    {"name": "بيتزا مارغريتا", "quantity": 300},              # raw grams still works
    {"name": "فته شورما",           "quantity": "طبق"},            # not in RAG → web search
]

print("=" * 60)
print("Running calculate_order_calories...")
print("=" * 60)

results = calculate_order_calories(
    order, vectorstore, llm,
    all_dishes=all_dishes,
    json_path=JSON_PATH,
)

print("\n── Results ──────────────────────────────────────────────")
for r in results:
    if r["found"]:
        src = f"[{r['source']}]"
        print(
            f"  OK {src:<6} {r['name']:<30} "
            f"'{r['quantity']}' = {r['quantity_grams']}g "
            f"x {r['calories_per_100g']} cal/100g "
            f"= {r['calories_per_meal']} kcal"
        )
    else:
        print(f"  --         {r['name']:<30} NOT FOUND anywhere")

print("\n── JSON output (for next agent) ─────────────────────────")
output = [
    {
        "name":           r["name"],
        "quantity":       r["quantity"],
        "quantity_grams": r["quantity_grams"],
        "calories_per_meal": r["calories_per_meal"],
        "found":          r["found"],
    }
    for r in results
]
print(json.dumps(output, ensure_ascii=False, indent=2))
