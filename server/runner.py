"""Drive the Scout graph + post-Scout pipeline, yielding frontend AgentEvents.

This is the server-side analogue of web/src/lib/agent-client.ts. It runs the
real LangGraph graph (so HITL interrupts, Apify/Tavily tools and RAG all fire)
and translates each phase into the same event vocabulary the UI already speaks.

The graph runs synchronously (LangGraph .invoke), so we execute it in a thread
pool and surface progress events around the blocking calls.
"""

from __future__ import annotations

import asyncio
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncGenerator

from langgraph.types import Command

import config
from pipeline import run_post_scout_pipeline
from .serializers import interrupt_to_event, nutrition_event, order_event
from .session import Session, store

AgentEvent = dict[str, Any]

_RAG_DATA = Path(__file__).resolve().parent.parent / "RAG" / "data.json"


@lru_cache(maxsize=1)
def _rag_dishes() -> list[dict]:
    try:
        return json.loads(_RAG_DATA.read_text(encoding="utf-8"))
    except Exception:
        return []


def _ingredients_for(dish_name: str) -> list[str]:
    """Best-effort ingredient lookup from the RAG dish data by name overlap."""
    name = (dish_name or "").strip()
    if not name:
        return []
    tokens = [t for t in re.split(r"\s+", name) if len(t) >= 2]
    for dish in _rag_dishes():
        dn = str(dish.get("name", ""))
        if dn and (dn in name or name in dn or any(t in dn for t in tokens)):
            return dish.get("ingredients", []) or []
    return []


def _agents(**status: str) -> AgentEvent:
    """Build an `agents` event. Unspecified agents default to idle."""
    defaults = {"orchestrator": "idle", "scout": "idle", "food": "idle", "order": "idle"}
    defaults.update(status)
    names = {
        "orchestrator": "Orchestrator",
        "scout": "Scout",
        "food": "Food",
        "order": "Order",
    }
    return {
        "type": "agents",
        "agents": [{"id": k, "name": names[k], "status": v} for k, v in defaults.items()],
    }


def _thinking(agent: str, label: str, done: bool = False) -> AgentEvent:
    return {"type": "thinking", "step": {"id": label, "agent": agent, "label": label, "done": done}}


async def _to_thread(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


async def start_run(thread_id: str, query: str, location: str, coords: dict) -> AsyncGenerator[AgentEvent, None]:
    """Classify the message (Orchestrator), then route to the right mode:
        A — order food            -> Scout (HITL) -> enrich -> order
        B — food question         -> RAG answer (Arabic)
        C — calorie filter+order  -> pick a dish under the limit -> Scout
        UNCLEAR                   -> ask one Arabic clarifying question
    """
    session = store.get_or_create(thread_id)

    yield _agents(orchestrator="active")
    yield _thinking("orchestrator", "بنفهم طلبك… 🧠")

    try:
        intent = await _to_thread(_classify_message, query)
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"معلش، حصلت مشكلة وإحنا بنفهم طلبك: {exc}"}
        yield {"type": "done"}
        return

    yield _thinking("orchestrator", "بنفهم طلبك… 🧠", done=True)
    mode = intent.get("mode", "UNCLEAR")
    what = (intent.get("what") or "").strip() or query

    # ---- Mode B: food question — answer from RAG, no ordering ----
    if mode == "B":
        async for ev in _answer_question(query):
            yield ev
        return

    # ---- UNCLEAR: ask one clarifying question; next message re-classifies ----
    if mode == "UNCLEAR":
        q = intent.get("clarification") or "ممكن توضّحلي أكتر؟ تطلب أكل، ولا تسأل عن طبق، ولا أكل بسعرات معيّنة؟"
        yield {"type": "token", "text": q}
        yield _agents(orchestrator="done")
        yield {"type": "done"}
        return

    # ---- Mode C: calorie filter, then order the top match ----
    search_query = query
    if mode == "C":
        yield _thinking("food", "بندوّرلك على أكلات تناسب السعرات… 🥗")
        try:
            matches, limit = await _to_thread(_dishes_under_calories, what)
        except Exception:  # noqa: BLE001
            matches, limit = [], 500.0
        yield _thinking("food", "بندوّرلك على أكلات تناسب السعرات… 🥗", done=True)
        if matches:
            top = "، ".join(matches[:5])
            yield {"type": "token", "text": f"لقيتلك أكلات تحت {int(limit)} سعرة 👌: {top}.\nهبدأ أدوّرلك على **{matches[0]}** قريّب منك.\n\n"}
            search_query = matches[0]
        else:
            yield {"type": "token", "text": f"معلِش، ملقيتش أكلات تحت {int(limit)} سعرة في قاعدة المعرفة. هدوّرلك على طلبك زي ما هو.\n\n"}

    # ---- Mode A (and Mode C after filtering): order via Scout ----
    yield {"type": "token", "text": f"حاضر! 😋 بندوّرلك على أحسن أماكن قريّبة منك في {location}.\n\n"}
    yield _agents(orchestrator="done", scout="active")
    yield _thinking("scout", "بندوّرلك على أقرب المطاعم ليك… 📍")
    yield _thinking("scout", "بنجمعلك التقييمات والمسافات — ممكن تاخد لحظات ⏳")
    yield _thinking("scout", "بنرتّبلك أحسن ٥ مطاعم على مقاسك ⭐")

    state = {
        "user_query": search_query,
        "location_query": location,
        "user_coords": coords,
    }

    try:
        result = await _to_thread(store.graph.invoke, state, session.config)
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"معلش، حصلت مشكلة وإحنا بندوّر على المطاعم: {exc}"}
        yield {"type": "done"}
        return

    yield _thinking("scout", "بندوّرلك على أقرب المطاعم ليك… 📍", done=True)
    yield _thinking("scout", "بنجمعلك التقييمات والمسافات — ممكن تاخد لحظات ⏳", done=True)
    yield _thinking("scout", "بنرتّبلك أحسن ٥ مطاعم على مقاسك ⭐", done=True)

    async for event in _emit_interrupt_or_finish(session, result):
        yield event


def _classify_message(message: str) -> dict:
    """Classify the message. Prefer the orchestrator's LLM classifier, but if that
    fails — e.g. the RAG model can't load due to low memory (error 1455) — fall
    back to a lightweight keyword classifier so ORDERING still works."""
    try:
        from orchestrator import classify_message

        return classify_message(message)
    except Exception as exc:  # noqa: BLE001
        print(f"[classify] orchestrator unavailable ({exc}); using keyword fallback", flush=True)
        return _keyword_classify(message)


def _keyword_classify(message: str) -> dict:
    """Model-free classifier: keyword heuristics for Arabic/English. Good enough
    to keep the app working when the LLM/RAG can't load."""
    import re as _re

    m = (message or "").strip()
    low = m.lower()
    has_calorie = bool(_re.search(r"سعر|سعرة|سعرات|كالوري|calorie|kcal", low))
    is_question = bool(_re.search(r"\?|؟|كام|إيه|ايه|مكونات|مكوّنات|كم سعر|what|how many|ingredient", low))

    if has_calorie and not is_question:
        return {"mode": "C", "what": m, "where": "", "clarification": ""}
    if is_question:
        return {"mode": "B", "what": m, "where": "", "clarification": ""}
    if m:
        # Default: treat a plain craving as an order.
        return {"mode": "A", "what": m, "where": "", "clarification": ""}
    return {"mode": "UNCLEAR", "what": "", "where": "",
            "clarification": "ممكن توضّحلي إنت عايز إيه؟"}


def _dishes_under_calories(constraint: str):
    """Calorie filter. Falls back to a direct data.json scan (no model) if the
    orchestrator can't load."""
    try:
        from orchestrator import dishes_under_calories

        return dishes_under_calories(constraint)
    except Exception:  # noqa: BLE001
        import json as _json
        import re as _re
        from pathlib import Path as _Path
        from RAG.Rag import find_dishes_by_calorie_constraint, _parse_cal_per_100g  # noqa: F401

        try:
            limit = float(_re.search(r"\d+(?:\.\d+)?", constraint).group())
        except (AttributeError, ValueError):
            limit = 500.0
        data = _Path(__file__).resolve().parent.parent / "RAG" / "data.json"
        dishes = _json.loads(data.read_text(encoding="utf-8"))
        return find_dishes_by_calorie_constraint(limit, dishes, str(data)), limit


def _answer_from_json(question: str) -> str:
    """Model-free Mode B answer: exact dish match from data.json → Arabic reply
    with real calories + ingredients. Used when the LLM/RAG can't load."""
    from RAG.Rag import _dish_context_from_json

    _, dish = _dish_context_from_json(question, _rag_dishes())
    if not dish:
        return "معلش، معنديش معلومات كافية عن الطبق ده دلوقتي. تحب تسألني عن طبق تاني؟"
    name = dish.get("name", "")
    cal = dish.get("calories_per_100g", "")
    ings = "، ".join(dish.get("ingredients", [])[:12])
    parts = [f"**{name}**"]
    if cal:
        parts.append(f"🔥 السعرات: {cal}")
    if ings:
        parts.append(f"🥗 المكوّنات: {ings}")
    return "\n".join(parts)


async def _answer_question(question: str) -> AsyncGenerator[AgentEvent, None]:
    """Mode B: stream an Arabic RAG answer to a food question."""
    yield _agents(orchestrator="done", food="active")
    yield _thinking("food", "بدوّرلك على الإجابة في قاعدة المعرفة… 📚")
    try:
        from orchestrator import answer_food_question

        answer = await _to_thread(answer_food_question, question)
    except Exception:  # noqa: BLE001 — orchestrator/model unavailable → model-free answer
        answer = await _to_thread(_answer_from_json, question)
    yield _thinking("food", "بدوّرلك على الإجابة في قاعدة المعرفة… 📚", done=True)
    yield {"type": "token", "text": answer}
    yield _agents(orchestrator="done", food="done")
    yield {"type": "done"}


async def resume_run(thread_id: str, resume: dict) -> AsyncGenerator[AgentEvent, None]:
    """Resume a paused conversation with the user's selection."""
    session = store.get(thread_id)
    if session is None:
        yield {"type": "error", "message": "المحادثة مش موجودة. ابدأ محادثة جديدة."}
        yield {"type": "done"}
        return

    command = _resume_command(resume)

    kind = resume.get("kind")
    if kind == "restaurant":
        yield _agents(orchestrator="done", scout="active")
        yield {"type": "token", "text": "اختيار جميل! 👌 بنجيبلك المنيو وأحسن العروض من المطعم ده.\n\n"}
        yield _thinking("scout", "بنفتحلك منيو المطعم… 🍽️")
        yield _thinking("scout", "بندوّرلك على العروض والخصومات — ثواني وهيظهرلك ⏳")
        yield _thinking("scout", "بنختارلك أحلى الأطباق بأحسن سعر 💛")
    elif kind == "deal":
        yield _agents(orchestrator="done", scout="done", food="active")
        yield _thinking("food", "بنحسبلك السعرات الحرارية للوجبة… 🔥")

    try:
        result = await _to_thread(store.graph.invoke, command, session.config)
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"معلش، حصلت مشكلة بسيطة. جرّب تاني من فضلك: {exc}"}
        yield {"type": "done"}
        return

    async for event in _emit_interrupt_or_finish(session, result):
        yield event


def _resume_command(resume: dict) -> Command:
    kind = resume.get("kind")
    if kind == "restaurant":
        return Command(resume=int(resume["index"]))
    if kind == "deal":
        return Command(resume={"index": int(resume["index"]), "quantity": int(resume.get("quantity", 1))})
    if kind == "no_deals":
        return Command(resume=int(resume["index"]))
    raise ValueError(f"Unknown resume kind: {kind!r}")


async def _emit_interrupt_or_finish(session: Session, result: dict) -> AsyncGenerator[AgentEvent, None]:
    """If the graph paused, emit the interrupt; otherwise run the pipeline."""
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        yield interrupt_to_event(payload)
        return

    payload = result.get("payload")
    if not payload:
        # menu_not_found path. If the user asked to see the restaurant's info
        # (show_info), present its address + phone clearly so they can call.
        restaurant = result.get("selected_restaurant") or {}
        if result.get("no_deals_action") == "show_info" and restaurant:
            yield {"type": "token", "text": _restaurant_info_text(restaurant)}
        else:
            yield {"type": "token", "text": "معلش، ملقيتش منيو متاح للمطعم ده. تحب أدوّرلك على مطعم تاني؟ 🙏"}
        yield {"type": "done"}
        return

    session.last_payload = payload
    async for event in _run_pipeline(payload):
        yield event


def _restaurant_info_text(restaurant: dict) -> str:
    """Markdown with the restaurant's contact details + a tappable call link."""
    name = restaurant.get("name") or "المطعم"
    address = restaurant.get("address") or "غير متوفر"
    phone = restaurant.get("phone") or ""
    rating = restaurant.get("rating")

    lines = [f"**{name}** 🏪", "", f"📍 العنوان: {address}"]
    if phone:
        tel = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        lines.append(f"📞 الهاتف: [{phone}](tel:{tel}) — اضغط للاتصال")
    else:
        lines.append("📞 الهاتف: غير متوفر")
    if rating:
        lines.append(f"⭐ التقييم: {rating}")
    lines += ["", "تقدر تتصل بالمطعم مباشرةً وتطلب منهم. بالهنا والشفا! 😋"]
    return "\n".join(lines)


async def _run_pipeline(payload: dict) -> AsyncGenerator[AgentEvent, None]:
    """Run RAG enrichment + order finalization, emitting Food/Order events."""
    deal = payload.get("selected_deal", {})
    meal = deal.get("item_name", "وجبتك")
    intent = payload.get("user_intent") or meal

    yield _agents(scout="done", food="active")
    yield _thinking("food", "بنشوفلك مكوّنات الوجبة… 🥗")
    yield _thinking("food", "بنحسبلك السعرات الحرارية — ثواني ⏳")

    rag_enabled = config.has_azure_openai()
    try:
        result = await _to_thread(run_post_scout_pipeline, payload, rag_enabled=rag_enabled)
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"معلش، حصلت مشكلة وإحنا بنجهّز طلبك: {exc}"}
        yield {"type": "done"}
        return

    yield _thinking("food", "بنشوفلك مكوّنات الوجبة… 🥗", done=True)
    yield _thinking("food", "بنحسبلك السعرات الحرارية — ثواني ⏳", done=True)

    ingredients = _ingredients_for(intent) or _ingredients_for(meal)
    nutrition = nutrition_event(result.get("rag_enrichment", {}), meal, ingredients)
    if nutrition:
        yield nutrition

    yield _agents(scout="done", food="done", order="active")
    yield _thinking("order", "بندوّرلك على كوبونات وخصومات شغّالة… 🎟️")
    yield _thinking("order", "بنجهّزلك الطلب وبنحسب السعر النهائي ✅")

    yield order_event(result, payload)
    yield _thinking("order", "بندوّرلك على كوبونات وخصومات شغّالة… 🎟️", done=True)
    yield _thinking("order", "بنجهّزلك الطلب وبنحسب السعر النهائي ✅", done=True)

    yield {"type": "token", "text": "طلبك جاهز! 🎉 تقدر تتصل بالمطعم مباشرةً من زرار الطلب تحت. بالهنا والشفا! 😋\n"}
    yield _agents(orchestrator="done", scout="done", food="done", order="done")
    yield {"type": "done"}
