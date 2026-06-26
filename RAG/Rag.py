import json
import os
import re
import shutil
import sys

# allow `import config` to find the project root when this file is run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ddgs import DDGS

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import config


# ─────────────────────────────────────────────
# 1. DOCUMENT LOADER
# ─────────────────────────────────────────────
def load_documents(json_path: str) -> tuple[list[Document], list[dict]]:
    with open(json_path, "r", encoding="utf-8") as f:
        dishes = json.load(f)

    docs = []
    for dish in dishes:
        ingredients = "، ".join(dish.get("ingredients", []))
        content = (
            f"اسم الطبق: {dish['name']}\n"
            f"الوصف: {dish['description']}\n"
            f"السعرات الحرارية لكل 100 غرام: {dish['calories_per_100g']}\n"
            f"المكونات: {ingredients}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "id":       str(dish["id"]),
                "name":     dish["name"],
                "calories": dish["calories_per_100g"],
            }
        ))

    return docs, dishes


# ─────────────────────────────────────────────
# 2. BUILD / LOAD CHROMADB
# ─────────────────────────────────────────────
def build_vectorstore(
    docs:        list[Document],
    embeddings:  HuggingFaceEmbeddings,
    persist_dir: str = "./chroma_dishes_db",
) -> Chroma:
    collection_name = "egyptian_dishes"

    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        print(" Loading existing ChromaDB from disk...")
        return Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )

    print(" Building ChromaDB from scratch (one-time)...")
    vs = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
    print(f" Indexed {len(docs)} dishes - saved to '{persist_dir}'")
    return vs


# ─────────────────────────────────────────────
# 3. BUILD PIPELINE
# ─────────────────────────────────────────────
def build_rag_pipeline(
    json_path:    str,
    persist_dir:  str = "./chroma_dishes_db",
) -> tuple[Chroma, object, list[dict]]:
    docs, all_dishes = load_documents(json_path)
    print(f" Loaded {len(docs)} dish documents from JSON.")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = build_vectorstore(docs, embeddings, persist_dir)

    llm = config.get_azure_openai_llm(temperature=0.2)

    return vectorstore, llm, all_dishes


# ─────────────────────────────────────────────
# 4. DISH LOOKUP BY NAME
#    Exact match first, semantic fallback second.
# ─────────────────────────────────────────────
def lookup_dish_by_name(dish_name: str, vectorstore: Chroma) -> dict | None:
    """
    Returns metadata dict {id, name, calories} or None if not found.
    Step 1 — exact metadata filter (fast, no embedding needed).
    Step 2 — semantic fallback for transliterations / spelling variants.
    """
    try:
        result = vectorstore.get(where={"name": dish_name})
        if result and result["metadatas"]:
            meta = result["metadatas"][0]
            print(f"   [RAG] Exact match -> {meta['name']} | {meta['calories']}")
            return meta
    except Exception as e:
        print(f"   [RAG] Exact lookup error: {e}")

    try:
        results = vectorstore.similarity_search_with_score(dish_name, k=1)
        if results:
            doc, score = results[0]
            # cosine distance < 0.60 catches transliterations (e.g. "Om Ali" -> أم علي)
            if score < 0.60:
                print(f"   [RAG] Semantic match -> {doc.metadata['name']} "
                      f"(score={score:.3f}) | {doc.metadata['calories']}")
                return doc.metadata
            else:
                print(f"   [RAG] Semantic score too low ({score:.3f}) -- treating as MISS")
    except Exception as e:
        print(f"   [RAG] Semantic lookup error: {e}")

    print(f"   [RAG] MISS -- '{dish_name}' not found")
    return None


# ─────────────────────────────────────────────
# 5. PERSISTENCE HELPERS
#    Saves web-found dishes to JSON + ChromaDB
#    so future lookups are instant.
# ─────────────────────────────────────────────
def dish_exists_in_json(dish_name: str, json_path: str) -> bool:
    with open(json_path, "r", encoding="utf-8") as f:
        all_dishes = json.load(f)
    return any(d["name"].strip() == dish_name.strip() for d in all_dishes)


def persist_new_dish(
    dish_data:   dict,
    json_path:   str,
    vectorstore: Chroma,
    all_dishes:  list[dict],
) -> dict:
    if dish_exists_in_json(dish_data["name"], json_path):
        print(f"   [Persist] '{dish_data['name']}' already in JSON -- skipping.")
        return dish_data

    with open(json_path, "r", encoding="utf-8") as f:
        current = json.load(f)

    new_id = max(d["id"] for d in current) + 1
    dish_data["id"]     = new_id
    dish_data["source"] = "web_search"

    current.append(dish_data)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    print(f"   [Persist] JSON updated -> [{new_id}] {dish_data['name']}")

    ingredients = "، ".join(dish_data.get("ingredients", []))
    content = (
        f"اسم الطبق: {dish_data['name']}\n"
        f"الوصف: {dish_data.get('description', '')}\n"
        f"السعرات الحرارية لكل 100 غرام: {dish_data['calories_per_100g']}\n"
        f"المكونات: {ingredients}"
    )
    vectorstore.add_documents([Document(
        page_content=content,
        metadata={
            "id":       str(new_id),
            "name":     dish_data["name"],
            "calories": dish_data["calories_per_100g"],
            "source":   "web_search",
        }
    )])
    print(f"   [Persist] ChromaDB updated -- total docs: {vectorstore._collection.count()}")

    all_dishes.append(dish_data)
    return dish_data


# ─────────────────────────────────────────────
# 6. WEB SEARCH CALORIE FALLBACK
#    Called when a dish is not found in the RAG.
# ─────────────────────────────────────────────
def web_search_calories(
    dish_name:   str,
    llm:         object,
    vectorstore: Chroma,
    all_dishes:  list[dict],
    json_path:   str,
) -> float | None:
    queries = [
        f"{dish_name} calories per 100g",
        f"{dish_name} سعرات حرارية لكل 100 جرام",
    ]

    raw_results = []
    for query in queries:
        print(f"   [WebSearch] Searching: '{query}'")
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=4))
            if raw_results:
                break
        except Exception as e:
            print(f"   [WebSearch] Search error: {e}")
            continue

    if not raw_results:
        print(f"   [WebSearch] No results found for '{dish_name}'.")
        return None

    snippets = "\n".join(
        f"- {r.get('title','')}: {r.get('body','')}"
        for r in raw_results
    )

    extract_prompt = ChatPromptTemplate.from_template(
        """أنت خبير تغذية. استخرج عدد السعرات الحرارية لكل 100 جرام من الطبق التالي.

الطبق: {dish}

نتائج البحث:
{snippets}

مهم جداً: أجب برقم واحد فقط يمثل السعرات الحرارية لكل 100 جرام.
إذا لم تجد معلومة دقيقة، قدّر بناءً على مكونات الطبق المعروفة.
لا تكتب أي كلمات أو وحدات — رقم فقط.

السعرات لكل 100 جرام:"""
    )

    raw = (extract_prompt | llm | StrOutputParser()).invoke(
        {"dish": dish_name, "snippets": snippets}
    ).strip()

    m = re.search(r"\d+(?:\.\d+)?", raw)
    if not m:
        print(f"   [WebSearch] Could not extract calorie number.")
        return None

    cal_per_100g = float(m.group())
    print(f"   [WebSearch] Found {cal_per_100g} cal/100g for '{dish_name}'")

    persist_new_dish(
        dish_data={
            "name":              dish_name,
            "description":       "طبق تم إضافته تلقائياً عبر البحث على الإنترنت.",
            "calories_per_100g": f"{int(cal_per_100g)} سعرة لكل 100 غرام",
            "ingredients":       [],
        },
        json_path=json_path,
        vectorstore=vectorstore,
        all_dishes=all_dishes,
    )

    return cal_per_100g


# ─────────────────────────────────────────────
# 7. QUANTITY PARSER
#    Converts Egyptian quantity expressions to grams.
# ─────────────────────────────────────────────
def parse_quantity_to_grams(dish_name: str, quantity: str | float, llm: object) -> float:
    if isinstance(quantity, (int, float)):
        return float(quantity)

    prompt = ChatPromptTemplate.from_template("""أنت خبير في تقدير الكميات في السياق المصري.
مهمتك: تحويل وصف الكمية إلى وزن بالجرام فقط.

الطبق: {dish}
الكمية المذكورة: {quantity}

قواعد مهمة:
- ربع كيلو = 250 جرام
- نص كيلو / نصف كيلو = 500 جرام
- تلت كيلو = 333 جرام
- كيلو = 1000 جرام
- رغيف / عيش = 80 جرام (خبز بلدي واحد)
- طبق / صحن = الكمية المعتادة للطبق (قدر بناءً على الطبق المذكور)
- علبة = 200 جرام تقريباً
- وجبة = الحجم المعتاد للوجبة الواحدة
- حبة = قطعة واحدة (قدر وزنها بناءً على الصنف)
- كوباية = 240 جرام

مهم جداً: أجب برقم واحد فقط يمثل الوزن بالجرام. لا تكتب أي كلمات أو وحدات.
مثال: إذا كانت الكمية "ربع كيلو"، اكتب فقط: 250

الوزن بالجرام:""")

    result = (prompt | llm | StrOutputParser()).invoke(
        {"dish": dish_name, "quantity": quantity}
    ).strip()

    m = re.search(r"\d+(?:\.\d+)?", result)
    if m:
        grams = float(m.group())
        print(f"   [Quantity] '{quantity}' -> {grams}g")
        return grams

    print(f"   [Quantity] Could not parse '{quantity}', defaulting to 200g")
    return 200.0


# ─────────────────────────────────────────────
# 8. CALORIE AGENT  ← main entry point
#    Input:  [{"name": str, "quantity": str | float}, ...]
#    Output: [{"name": str, "quantity_grams": float,
#              "calories_per_meal": float, "found": bool,
#              "source": "rag" | "web" | None}, ...]
# ─────────────────────────────────────────────
def _parse_cal_per_100g(cal_str: str) -> float | None:
    m = re.search(r"\d+", cal_str)
    return float(m.group()) if m else None


def calculate_order_calories(
    order:       list[dict],
    vectorstore: Chroma,
    llm:         object,
    all_dishes:  list[dict] | None = None,
    json_path:   str = "data.json",
) -> list[dict]:
    results = []
    for item in order:
        dish_name = item.get("name", "")
        quantity  = item.get("quantity", item.get("quantity_grams", 0))

        quantity_grams = parse_quantity_to_grams(dish_name, quantity, llm)
        meta = lookup_dish_by_name(dish_name, vectorstore)

        if meta is None:
            cal_per_100g = web_search_calories(
                dish_name, llm, vectorstore, all_dishes or [], json_path
            )
            if cal_per_100g is None:
                results.append({
                    "name":              dish_name,
                    "quantity":          quantity,
                    "quantity_grams":    quantity_grams,
                    "calories_per_100g": None,
                    "calories_per_meal":    None,
                    "found":             False,
                    "source":            None,
                })
            else:
                results.append({
                    "name":              dish_name,
                    "quantity":          quantity,
                    "quantity_grams":    quantity_grams,
                    "calories_per_100g": cal_per_100g,
                    "calories_per_meal":    round((cal_per_100g / 100) * quantity_grams, 1),
                    "found":             True,
                    "source":            "web",
                })
            continue

        cal_per_100g = _parse_cal_per_100g(str(meta.get("calories", "")))
        results.append({
            "name":              dish_name,
            "quantity":          quantity,
            "quantity_grams":    quantity_grams,
            "calories_per_100g": cal_per_100g,
            "calories_per_meal":    round((cal_per_100g / 100) * quantity_grams, 1) if cal_per_100g else None,
            "found":             True,
            "source":            "rag",
        })

    return results


# ─────────────────────────────────────────────
# UTILITY: wipe ChromaDB to force a rebuild
# Run once after changing data.json or the embedding model.
# ─────────────────────────────────────────────
def web_search_dish_details(
    dish_name:   str,
    llm:         object,
    vectorstore: object,
    all_dishes:  list[dict],
    json_path:   str,
) -> dict | None:
    """Search the web for description, ingredients, and calories, then persist."""
    queries = [
        f"{dish_name} description ingredients and calories per 100g",
        f"{dish_name} وصف ومكونات وسعرات حرارية",
    ]

    raw_results = []
    for query in queries:
        print(f"   [WebSearch] Searching: '{query}'")
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=4))
            if raw_results:
                break
        except Exception as e:
            print(f"   [WebSearch] Search error: {e}")
            continue

    if not raw_results:
        print(f"   [WebSearch] No results found for '{dish_name}'.")
        return None

    snippets = "\n".join(
        f"- {r.get('title','')}: {r.get('body','')}"
        for r in raw_results
    )

    extract_prompt = ChatPromptTemplate.from_template(
        """أنت خبير تغذية وطباخ محترف. استخرج تفاصيل الطبق التالي بناءً على نتائج البحث.

الطبق: {dish}

نتائج البحث:
{snippets}

مهم جداً: أجب بتنسيق JSON فقط يحتوي على الحقول التالية:
- "name": اسم الطبق باللغة العربية
- "description": وصف قصير ومميز للطبق باللغة العربية
- "calories_per_100g": عدد السعرات الحرارية لكل 100 جرام (مثال: "150 سعرة لكل 100 غرام")
- "ingredients": قائمة بالمكونات الرئيسية للطبق باللغة العربية

إذا لم تجد معلومات دقيقة، قدّر المكونات والسعرات بناءً على معرفتك بالطبق.
لا تكتب أي نصوص خارج الـ JSON.

مخرج الـ JSON:"""
    )

    raw = (extract_prompt | llm | StrOutputParser()).invoke(
        {"dish": dish_name, "snippets": snippets}
    ).strip()

    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            dish_data = json.loads(match.group(0))
            if "name" in dish_data and "calories_per_100g" in dish_data:
                persisted = persist_new_dish(
                    dish_data=dish_data,
                    json_path=json_path,
                    vectorstore=vectorstore,
                    all_dishes=all_dishes,
                )
                return persisted
    except Exception as e:
        print(f"   [WebSearch] JSON parse / persist error: {e}")

    return None


def query_rag(
    query: str,
    vectorstore: object,
    llm: object,
    all_dishes: list[dict],
    json_path: str,
) -> str:
    """Answer a free-text question about a dish using RAG with web fallback."""
    extract_dish_prompt = ChatPromptTemplate.from_template(
        """أنت خبير في تصنيف الأغذية. استخرج اسم الطبق أو الأكلة الرئيسي المذكور في السؤال التالي.
السؤال: {query}
أجب باسم الأكلة فقط، دون أي كلمات أخرى أو علامات ترقيم. إذا كان هناك أكثر من أكلة، اختر الأكلة الرئيسية.
اسم الأكلة:"""
    )
    dish_name = (extract_dish_prompt | llm | StrOutputParser()).invoke({"query": query}).strip()
    dish_name = re.sub(r'["\'\.]', '', dish_name).strip()

    print(f"   [RAG Query] Extracted dish name: '{dish_name}'")

    meta = lookup_dish_by_name(dish_name, vectorstore)
    dish = None
    if meta:
        dish_id = int(meta.get("id"))
        dish = next((d for d in all_dishes if d["id"] == dish_id), None)

    if not dish:
        print(f"   [RAG Query] Dish '{dish_name}' not found in RAG. Performing web search fallback...")
        dish = web_search_dish_details(dish_name, llm, vectorstore, all_dishes, json_path)

    if not dish:
        return f"عذراً، لم أتمكن من العثور على معلومات عن طبق '{dish_name}'."

    answer_prompt = ChatPromptTemplate.from_template(
        """أنت خبير تغذية ومساعد عملاء ودود في Food Pilot.
أجب عن سؤال العميل التالي بدقة ومودة، مستعيناً بالمعلومات المتاحة عن الطبق.

سؤال العميل: {query}

معلومات الطبق:
- اسم الطبق: {name}
- الوصف: {description}
- السعرات الحرارية: {calories}
- المكونات: {ingredients}

صِغ الإجابة باللغة التي سأل بها العميل (سواء كانت العربية أو الإنجليزية). كن مفصلاً وودوداً.
الإجابة:"""
    )

    ingredients_str = "، ".join(dish.get("ingredients", []))
    answer = (answer_prompt | llm | StrOutputParser()).invoke({
        "query": query,
        "name": dish.get("name"),
        "description": dish.get("description"),
        "calories": dish.get("calories_per_100g"),
        "ingredients": ingredients_str or "غير محددة",
    }).strip()

    return answer


# ─────────────────────────────────────────────
# UTILITY: wipe ChromaDB to force a rebuild
# Run once after changing data.json or the embedding model.
# ─────────────────────────────────────────────
def reset_vectorstore(persist_dir: str = "./chroma_dishes_db"):
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        print(f"  Deleted '{persist_dir}'. Will rebuild on next run.")


# ─────────────────────────────────────────────
# 9. CALORIE FILTER
#    Returns dish names whose estimated serving calories
#    (cal_per_100g * 2.5 for a 250g portion) fall under the limit.
# ─────────────────────────────────────────────
def find_dishes_by_calorie_constraint(
    calorie_limit: float,
    all_dishes: list[dict],
) -> list[str]:
    matching_dishes = []
    for dish in all_dishes:
        cal_str = dish.get("calories_per_100g", "")
        match = re.search(r'\d+', str(cal_str))
        if match:
            cal_100g = float(match.group())
            # 250g standard serving estimate
            if cal_100g * 2.5 <= calorie_limit:
                matching_dishes.append(dish["name"])
    return matching_dishes
