import json
import os
import re
import shutil

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
    """
    Returns:
      - docs       : LangChain Documents for embedding
      - all_dishes : Raw list kept in memory for aggregate/calorie queries
    """
    with open(json_path, "r", encoding="utf-8") as f:
        dishes = json.load(f)

    docs = []
    for dish in dishes:
        ingredients = "، ".join(dish.get("ingredients", []))
        content = (
            f"اسم الطبق: {dish['name']}\n"
            f"الوصف: {dish['description']}\n"
            f"السعرات الحرارية لكل 100 غرام: {dish['calories_per_100g']}\n"  # CHANGED
            f"المكونات: {ingredients}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "id":       str(dish["id"]),
                "name":     dish["name"],
                "calories": dish["calories_per_100g"],                         # CHANGED
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

    print(" Building ChromaDB from scratch (one-time, ~60 sec)...")
    vs = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
    print(f" Indexed {len(docs)} dishes → saved to '{persist_dir}'")
    return vs


# ─────────────────────────────────────────────
# 3. AGGREGATE QUERY DETECTION
#    Handles "how many", "list all", etc.
#    These CANNOT be answered by retrieval alone
#    because retrieval only returns k=N docs.
# ─────────────────────────────────────────────
AGGREGATE_PATTERNS = [
    r"كم\s*(عدد|وصفة|طبق|أكلة|وصفات|أطباق|أصناف)",
    r"how many (recipes|dishes|items|foods)",
    r"total (number|count|recipes|dishes)",
    r"(اذكر|اسرد|أعطني)\s*(جميع|كل)",
    r"(list|show|give me)\s*(all|every)",
    r"ما\s*هي\s*(جميع|كل)\s*(الأطباق|الوصفات|الأكلات)",
    r"all (dishes|recipes)",
]

def is_aggregate_query(question: str) -> bool:
    return any(re.search(p, question, re.IGNORECASE) for p in AGGREGATE_PATTERNS)


def handle_aggregate_query(
    question:   str,
    all_dishes: list[dict],
    llm:        ChatGroq,
) -> str:
    """
    For count/list questions, bypass retrieval entirely.
    Pass the FULL dish index to the LLM as a numbered list.
    """
    total = len(all_dishes)
    index = "\n".join(
        f"{d['id']}. {d['name']} ({d['calories_per_100g']})"  # CHANGED
        for d in all_dishes
    )

    prompt = ChatPromptTemplate.from_template(
        """أنت مساعد طهي. لديك قائمة كاملة بـ {total} وصفة طعام:

{index}

السؤال: {question}

أجب بدقة بناءً على القائمة الكاملة أعلاه. الإجابة:"""
    )

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"total": total, "index": index, "question": question})


# ─────────────────────────────────────────────
# 4. CALORIE FILTER
#    Semantic search cannot do math.
#    We parse calorie ranges directly from
#    all_dishes and filter numerically.
# ─────────────────────────────────────────────
CALORIE_PATTERNS = [
    # Arabic
    (r"أقل\s*من\s*(\d+)",               "less_than"),
    (r"تحت\s*(\d+)",                     "less_than"),
    (r"أكثر\s*من\s*(\d+)",              "greater_than"),
    (r"فوق\s*(\d+)",                     "greater_than"),
    (r"بين\s*(\d+)\s*و\s*(\d+)",        "between"),
    # English
    (r"less\s*than\s*(\d+)",            "less_than"),
    (r"under\s*(\d+)",                  "less_than"),
    (r"below\s*(\d+)",                  "less_than"),
    (r"more\s*than\s*(\d+)",            "greater_than"),
    (r"above\s*(\d+)",                  "greater_than"),
    (r"over\s*(\d+)",                   "greater_than"),
    (r"between\s*(\d+)\s*and\s*(\d+)", "between"),
]

def detect_calorie_query(question: str):
    """
    Returns (operator, val1, val2) or None.
    operator is one of: 'less_than', 'greater_than', 'between'
    """
    for pattern, op in CALORIE_PATTERNS:
        m = re.search(pattern, question, re.IGNORECASE)
        if m:
            if op == "between":
                return op, int(m.group(1)), int(m.group(2))
            else:
                return op, int(m.group(1)), None
    return None


def parse_calorie_range(calorie_str: str) -> tuple[int, int]:
    """
    Parses strings like:
      "120–150 سعرة لكل 100 غرام"
    Returns (min_cal, max_cal).
    """
    numbers = re.findall(r"\d+", calorie_str)
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        v = int(numbers[0])
        return v, v
    return 0, 0


def filter_dishes_by_calories(
    all_dishes: list[dict],
    operator:   str,
    val1:       int,
    val2:       int | None,
) -> list[dict]:
    """
    Filters dishes using the AVERAGE of their calorie range.
    avg = (min + max) / 2
    """
    matched = []
    for dish in all_dishes:
        lo, hi = parse_calorie_range(dish["calories_per_100g"])  # CHANGED
        avg = (lo + hi) / 2

        if operator == "less_than"     and avg < val1:
            matched.append(dish)
        elif operator == "greater_than" and avg > val1:
            matched.append(dish)
        elif operator == "between"      and val2 and val1 <= avg <= val2:
            matched.append(dish)

    return matched


def handle_calorie_query(
    question:   str,
    all_dishes: list[dict],
    operator:   str,
    val1:       int,
    val2:       int | None,
    llm:        ChatGroq,
) -> str:
    matched = filter_dishes_by_calories(all_dishes, operator, val1, val2)

    if not matched:
        return "لا توجد أطباق تطابق معيار السعرات الحرارية المطلوب في قاعدة البيانات."

    dish_list = "\n".join(
        f"  • {d['name']} — {d['calories_per_100g']}"  # CHANGED
        for d in matched
    )

    prompt = ChatPromptTemplate.from_template(
        """أنت مساعد طهي. وجدت {count} طبقاً يطابق معيار السعرات الحرارية:

{dish_list}

السؤال الأصلي: {question}

قدّم الإجابة بشكل منظم وواضح. الإجابة:"""
    )

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "count":     len(matched),
        "dish_list": dish_list,
        "question":  question,
    })


# ─────────────────────────────────────────────
# 5. DISH LOOKUP BY NAME  ← NEW
#    Agent 2's primary entry point.
#    Tries exact metadata match first (fast),
#    falls back to semantic search for spelling
#    variants and transliteration differences.
# ─────────────────────────────────────────────
def lookup_dish_by_name(
    dish_name:   str,
    vectorstore: Chroma,
    retriever,
) -> dict | None:
    """
    Returns a metadata dict with keys: id, name, calories
    Returns None if the dish is not found in the RAG.

    Step 1 — exact metadata filter: no embedding needed, O(1).
    Step 2 — semantic fallback: catches spelling variants, transliteration,
              partial names (e.g. "Om Ali" vs "أم علي").
              Only accepts the top result if similarity score < 0.35
              (cosine distance; lower = more similar).
    """
    # Step 1: exact name match via metadata filter
    try:
        result = vectorstore.get(where={"name": dish_name})
        if result and result["metadatas"]:
            meta = result["metadatas"][0]
            print(f"   [RAG] Exact match → {meta['name']} | {meta['calories']}")
            return meta
    except Exception as e:
        print(f"   [RAG] Exact lookup error: {e}")

    # Step 2: semantic fallback
    try:
        results = vectorstore.similarity_search_with_score(dish_name, k=1)
        if results:
            doc, score = results[0]
            # cosine distance threshold: 0.35 ≈ 65% similarity minimum
            if score < 0.35:
                print(f"   [RAG] Semantic match → {doc.metadata['name']} "
                      f"(score={score:.3f}) | {doc.metadata['calories']}")
                return doc.metadata
            else:
                print(f"   [RAG] Semantic score too low ({score:.3f}) — treating as MISS")
    except Exception as e:
        print(f"   [RAG] Semantic lookup error: {e}")

    print(f"   [RAG] MISS — '{dish_name}' not found")
    return None


# ─────────────────────────────────────────────
# 6. PERSISTENCE HELPERS  ← NEW
#    Used by Agent 2 when a dish is not in RAG.
#    Writes to JSON (source of truth) first,
#    then upserts into ChromaDB.
# ─────────────────────────────────────────────
def dish_exists_in_json(dish_name: str, json_path: str) -> bool:
    """
    Guard against duplicate writes if two requests race
    for the same unknown dish.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        all_dishes = json.load(f)
    return any(d["name"].strip() == dish_name.strip() for d in all_dishes)


def persist_new_dish(
    dish_data:   dict,
    json_path:   str,
    vectorstore: Chroma,
    all_dishes:  list[dict],
) -> dict:
    """
    Called by Agent 2 after a web search returns a new dish.

    dish_data must follow the schema:
        {
            "name":             str,   # Arabic or English
            "description":      str,
            "calories_per_100g": str,  # e.g. "150–190 سعرة لكل 100 غرام"
            "ingredients":      list[str]
        }

    Steps:
      1. Duplicate guard — skip if dish already in JSON.
      2. Assign new ID (max existing + 1).
      3. Append to JSON file (source of truth).
      4. Upsert one Document into ChromaDB (no full rebuild needed).
      5. Append to in-memory all_dishes so calorie/aggregate
         queries stay in sync for the rest of this session.

    Returns the dish dict with its assigned ID.
    """
    # Step 1: duplicate guard
    if dish_exists_in_json(dish_data["name"], json_path):
        print(f"   [Persist] '{dish_data['name']}' already in JSON — skipping write.")
        return dish_data

    # Step 2: assign ID
    with open(json_path, "r", encoding="utf-8") as f:
        current = json.load(f)

    new_id = max(d["id"] for d in current) + 1
    dish_data["id"]     = new_id
    dish_data["source"] = "web_search"   # provenance flag

    # Step 3: write to JSON
    current.append(dish_data)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    print(f"   [Persist] JSON updated → [{new_id}] {dish_data['name']}")

    # Step 4: upsert into ChromaDB
    ingredients = "، ".join(dish_data.get("ingredients", []))
    content = (
        f"اسم الطبق: {dish_data['name']}\n"
        f"الوصف: {dish_data.get('description', '')}\n"
        f"السعرات الحرارية لكل 100 غرام: {dish_data['calories_per_100g']}\n"
        f"المكونات: {ingredients}"
    )
    doc = Document(
        page_content=content,
        metadata={
            "id":       str(new_id),
            "name":     dish_data["name"],
            "calories": dish_data["calories_per_100g"],
            "source":   "web_search",
        }
    )
    vectorstore.add_documents([doc])
    print(f"   [Persist] ChromaDB updated — "
          f"total docs: {vectorstore._collection.count()}")

    # Step 5: update in-memory list for this session
    all_dishes.append(dish_data)

    return dish_data


# ─────────────────────────────────────────────
# 7. HYBRID RETRIEVAL WITH KEYWORD FALLBACK
#    If MMR semantic search returns < 2 results,
#    fall back to keyword matching inside ChromaDB.
# ─────────────────────────────────────────────
def retrieve_with_fallback(
    question:    str,
    retriever,
    vectorstore: Chroma,
    k:           int = 6,
) -> list[Document]:
    docs = retriever.invoke(question)

    if len(docs) < 2:
        print("   [Semantic retrieval weak → trying keyword fallback]")
        keywords = [w for w in question.split() if len(w) > 2]
        for kw in keywords:
            try:
                fallback = vectorstore.similarity_search(
                    question,
                    k=k,
                    where_document={"$contains": kw},
                )
                if fallback:
                    print(f"   [Keyword fallback matched on '{kw}']")
                    return fallback
            except Exception:
                continue

    return docs


def format_docs(docs: list[Document]) -> str:
    return "\n\n---\n\n".join(
        f"[الطبق رقم {d.metadata['id']}: {d.metadata['name']}]\n{d.page_content}"
        for d in docs
    )


# ─────────────────────────────────────────────
# 8. BUILD PIPELINE
# ─────────────────────────────────────────────
def build_rag_pipeline(
    json_path:    str,
    groq_api_key: str,
    persist_dir:  str = "./chroma_dishes_db",
):
    docs, all_dishes = load_documents(json_path)
    print(f" Loaded {len(docs)} dish documents from JSON.")

    # 512-token multilingual model — no truncation issues
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vectorstore = build_vectorstore(docs, embeddings, persist_dir)

    # MMR search: considers 30 candidates, returns best 6 diverse results
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k":           6,
            "fetch_k":     30,
            "lambda_mult": 0.7,
        },
    )

    llm = ChatGroq(
        api_key=groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
    )

    # total_count always injected so LLM knows real collection size
    prompt = ChatPromptTemplate.from_template(
        """أنت مساعد طهي متخصص في المطبخ المصري والعالمي.
قاعدة البيانات تحتوي على {total_count} وصفة طعام إجمالاً.
استخدم المعلومات المسترجعة أدناه للإجابة.
إذا لم تجد الإجابة في السياق، قل ذلك بوضوح ولا تختلق معلومات.
يمكنك الإجابة بنفس لغة السؤال (عربي أو إنجليزي).

السياق المسترجع:
{context}

السؤال: {question}

الإجابة:"""
    )

    return retriever, vectorstore, llm, prompt, all_dishes


# ─────────────────────────────────────────────
# 9. SMART QUERY FUNCTION
# ─────────────────────────────────────────────
def query_rag(
    question:    str,
    retriever,
    vectorstore: Chroma,
    llm:         ChatGroq,
    prompt:      ChatPromptTemplate,
    all_dishes:  list[dict],
) -> tuple[str, list[str]]:

    # Route 1: aggregate queries — bypass retrieval, use full index
    if is_aggregate_query(question):
        print("   [→ Route 1: Aggregate query — using full dish index]")
        answer = handle_aggregate_query(question, all_dishes, llm)
        return answer, []

    # Route 2: calorie filter — bypass retrieval, filter numerically
    calorie_result = detect_calorie_query(question)
    if calorie_result:
        operator, val1, val2 = calorie_result
        print(f"   [→ Route 2: Calorie query — operator: {operator}, "
              f"val1: {val1}, val2: {val2}]")
        answer = handle_calorie_query(question, all_dishes, operator, val1, val2, llm)
        return answer, []

    # Route 3: semantic search + keyword fallback
    print("   [→ Route 3: Semantic search]")
    docs = retrieve_with_fallback(question, retriever, vectorstore)

    if not docs:
        return "لم أجد أي وصفات مطابقة في قاعدة البيانات.", []

    chain  = prompt | llm | StrOutputParser()
    answer = chain.invoke({
        "context":     format_docs(docs),
        "question":    question,
        "total_count": len(all_dishes),
    })

    sources = list({d.metadata["name"] for d in docs})
    return answer, sources


# ─────────────────────────────────────────────
# 10. UTILITIES
# ─────────────────────────────────────────────
def reset_vectorstore(persist_dir: str = "./chroma_dishes_db"):
    """
    Wipe the persisted ChromaDB and rebuild on next run.
    Run this whenever you change the embedding model or JSON data.
    """
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        print(f"  Deleted '{persist_dir}'. Will rebuild on next run.")


def inspect_collection(vectorstore: Chroma):
    col   = vectorstore._collection
    count = col.count()
    print(f"\n ChromaDB | collection: '{col.name}' | total documents: {count}")
    for m in col.peek(limit=3)["metadatas"]:
        print(f"   • [{m['id']}] {m['name']} — {m['calories']}")
    print()


# ─────────────────────────────────────────────
# 11. ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    if not GROQ_API_KEY:
        raise ValueError(" GROQ_API_KEY not found. Make sure it is set in your .env file.")

    JSON_PATH   = "Egyptian_Dishes_Simplified.json"
    PERSIST_DIR = "./chroma_dishes_db"

    # ⚠️ Uncomment ONCE after updating the JSON (field name changed).
    # Comment out again after the first successful run.
    # reset_vectorstore(PERSIST_DIR)

    print(" Initialising RAG pipeline...")
    retriever, vectorstore, llm, prompt, all_dishes = build_rag_pipeline(
        JSON_PATH, GROQ_API_KEY, PERSIST_DIR
    )
    inspect_collection(vectorstore)
    print(f" Pipeline ready! ({len(all_dishes)} dishes indexed)\n")
    print("اكتب سؤالك أو اكتب 'exit' للخروج\n")

    sample_questions = [
        "كم عدد الوصفات في قاعدة البيانات؟",            # Route 1 — aggregate
        "اذكر لي جميع أطباق الحلويات",                   # Route 1 — aggregate
        "أي الأطباق تحتوي على أقل من 100 سعرة لكل 100 غرام؟",  # Route 2 — calorie filter
        "show me dishes between 100 and 150 calories",    # Route 2 — calorie filter
        "ما هي مكونات الكشري؟",                           # Route 3 — semantic
        "What are the ingredients of Om Ali?",             # Route 3 — semantic
        "ما الفرق بين الطعمية والفلافل الشامية؟",         # Route 3 — semantic
    ]

    print("── أمثلة على أسئلة يمكنك تجربتها ──")
    for i, q in enumerate(sample_questions, 1):
        print(f"  {i}. {q}")
    print()

    while True:
        question = input(" سؤالك: ").strip()

        if question.lower() in ("exit", "quit", "خروج", ""):
            print("مع السلامة! ")
            break

        answer, sources = query_rag(
            question, retriever, vectorstore, llm, prompt, all_dishes
        )

        print(f"\n الإجابة:\n{answer}")
        if sources:
            print(f"\n المصادر: {' | '.join(sources)}")
        print("─" * 60 + "\n")
