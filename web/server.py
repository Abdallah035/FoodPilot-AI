"""Food Pilot — Scout web app (FastAPI).

A chat-style UI that drives the LangGraph Scout agent through its two
human-in-the-loop steps with clickable buttons instead of the CLI prompts.

All user-facing text — prompts, status messages, AND the scraped restaurant /
menu data — is translated into the language the user typed in (Arabic or
English; dominant language wins for mixed input).

Run:
    uv run uvicorn web.server:app --reload
then open http://127.0.0.1:8000
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from agent1_scout import i18n
from agent1_scout.graph import build_graph

app = FastAPI(title="Food Pilot — Scout")

# one compiled graph (in-memory checkpointer) shared across sessions;
# each session is isolated by its own thread_id.
_GRAPH = build_graph()

# session_id -> {"thread_id": str, "lang": "ar"|"en"}
_SESSIONS: dict[str, dict] = {}

_STATIC = Path(__file__).parent / "static"


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class StartReq(BaseModel):
    query: str
    location: str = "Maadi, Cairo"
    lat: float = 29.96
    lon: float = 31.26


class PickRestaurantReq(BaseModel):
    session_id: str
    index: int


class PickDealReq(BaseModel):
    session_id: str
    index: int
    quantity: int = 1


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _session(session_id: str) -> dict:
    s = _SESSIONS.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Unknown or expired session.")
    return s


def _cfg(session: dict) -> dict:
    return {"configurable": {"thread_id": session["thread_id"]}}


def _ui(text: str, lang: str) -> str:
    return i18n.translate(text, lang)


def _restaurant_options(payload: dict, lang: str) -> list[dict]:
    """Translate restaurant option fields (reason, address) into `lang`."""
    opts = payload["options"]
    reasons = i18n.translate_many([o.get("reason", "") for o in opts], lang)
    addresses = i18n.translate_many([o.get("address", "") for o in opts], lang)
    out = []
    for o, reason, address in zip(opts, reasons, addresses):
        out.append(
            {
                "index": o["index"],
                "name": o["name"],  # proper name — left as-is
                "score": o["score"],
                "reason": reason,
                "address": address,
                "phone": o.get("phone", ""),
            }
        )
    return out


def _deal_options(payload: dict, lang: str) -> list[dict]:
    """Translate deal item names + descriptions into `lang`."""
    opts = payload["options"]
    names = i18n.translate_many([o.get("item_name", "") for o in opts], lang)
    descs = i18n.translate_many([o.get("deal_description", "") for o in opts], lang)
    out = []
    for o, name, desc in zip(opts, names, descs):
        out.append(
            {
                "index": o["index"],
                "item_name": name,
                "price": o["price"],
                "currency": o["currency"],
                "deal_description": desc,
            }
        )
    return out


def _restaurant_step(payload: dict, lang: str, session_id: str) -> dict:
    return {
        "step": "select_restaurant",
        "session_id": session_id,
        "lang": lang,
        "rtl": i18n.is_rtl(lang),
        "prompt": _ui("Pick a restaurant:", lang),
        "options": _restaurant_options(payload, lang),
    }


def _deal_step(payload: dict, lang: str, session_id: str) -> dict:
    if not payload["options"]:
        return {
            "step": "no_deals",
            "session_id": session_id,
            "lang": lang,
            "rtl": i18n.is_rtl(lang),
            "message": _ui("No deals were found for this restaurant.", lang),
        }
    return {
        "step": "select_deal",
        "session_id": session_id,
        "lang": lang,
        "rtl": i18n.is_rtl(lang),
        "prompt": _ui("Pick a deal and a quantity:", lang),
        "quantity_label": _ui("Quantity", lang),
        "confirm_label": _ui("Confirm order", lang),
        "options": _deal_options(payload, lang),
    }


def _final_step(payload: dict, lang: str, session_id: str) -> dict:
    return {
        "step": "done",
        "session_id": session_id,
        "lang": lang,
        "rtl": i18n.is_rtl(lang),
        "message": _ui("Your order is configured! Here is the summary:", lang),
        "summary": {
            "restaurant": payload["selected_restaurant"]["name"],
            "address": payload["selected_restaurant"].get("address", ""),
            "phone": payload["selected_restaurant"].get("phone", ""),
            "item": i18n.translate(payload["selected_deal"]["item_name"], lang),
            "price": payload["selected_deal"]["price"],
            "currency": payload["selected_deal"]["currency"],
            "quantity": payload["selected_deal"].get("quantity", 1),
        },
        "payload": payload,  # raw contract for the next agent
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.post("/api/start")
def start(req: StartReq) -> dict:
    lang = i18n.detect_lang(req.query)
    session_id = str(uuid.uuid4())
    session = {"thread_id": str(uuid.uuid4()), "lang": lang}
    _SESSIONS[session_id] = session

    state = {
        "user_query": req.query,
        "location_query": req.location,
        "user_coords": {"lat": req.lat, "lon": req.lon},
    }
    result = _GRAPH.invoke(state, _cfg(session))
    payload = result["__interrupt__"][0].value
    return _restaurant_step(payload, lang, session_id)


@app.post("/api/pick_restaurant")
def pick_restaurant(req: PickRestaurantReq) -> dict:
    session = _session(req.session_id)
    lang = session["lang"]
    result = _GRAPH.invoke(Command(resume=req.index), _cfg(session))
    payload = result["__interrupt__"][0].value
    return _deal_step(payload, lang, req.session_id)


@app.post("/api/pick_deal")
def pick_deal(req: PickDealReq) -> dict:
    session = _session(req.session_id)
    lang = session["lang"]
    result = _GRAPH.invoke(
        Command(resume={"index": req.index, "quantity": req.quantity}),
        _cfg(session),
    )
    payload = result["payload"]
    _SESSIONS.pop(req.session_id, None)  # session complete
    return _final_step(payload, lang, req.session_id)


# static assets (css/js if any) under /static
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
