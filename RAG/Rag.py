import json
import os
import re
import shutil
from ddgs import DDGS

from dotenv import load_dotenv
load_dotenv()

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq


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
    groq_api_key: str,
    persist_dir:  str = "./chroma_dishes_db",
) -> tuple[Chroma, ChatGroq, list[dict]]:
    docs, all_dishes = load_documents(json_path)
    print(f" Loaded {len(docs)} dish documents from JSON.")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = build_vectorstore(docs, embeddings, persist_dir)

    llm = ChatGroq(
        api_key=groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
    )

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
    llm:         ChatGroq,
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
def parse_quantity_to_grams(dish_name: str, quantity: str | float, llm: ChatGroq) -> float:
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
#              "total_calories": float, "found": bool,
#              "source": "rag" | "web" | None}, ...]
# ─────────────────────────────────────────────
def _parse_cal_per_100g(cal_str: str) -> float | None:
    m = re.search(r"\d+", cal_str)
    return float(m.group()) if m else None


def calculate_order_calories(
    order:       list[dict],
    vectorstore: Chroma,
    llm:         ChatGroq,
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
                    "total_calories":    None,
                    "found":             False,
                    "source":            None,
                })
            else:
                results.append({
                    "name":              dish_name,
                    "quantity":          quantity,
                    "quantity_grams":    quantity_grams,
                    "calories_per_100g": cal_per_100g,
                    "total_calories":    round((cal_per_100g / 100) * quantity_grams, 1),
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
            "total_calories":    round((cal_per_100g / 100) * quantity_grams, 1) if cal_per_100g else None,
            "found":             True,
            "source":            "rag",
        })

    return results


# ─────────────────────────────────────────────
# UTILITY: wipe ChromaDB to force a rebuild
# Run once after changing data.json or the embedding model.
# ─────────────────────────────────────────────
def reset_vectorstore(persist_dir: str = "./chroma_dishes_db"):
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        print(f"  Deleted '{persist_dir}'. Will rebuild on next run.")
