"""FastAPI bridge exposing the Food Pilot pipeline over Server-Sent Events.

Endpoints (consumed by web/src/lib/agent-client.ts `LiveAgentClient`):
    GET  /health            -> liveness probe
    POST /chat              -> start a run; streams SSE AgentEvents
    POST /resume            -> resume a paused run; streams SSE AgentEvents

Run locally:
    uv run uvicorn server.app:app --reload --port 8000
"""

from __future__ import annotations

import json
import sys
from typing import Any, AsyncGenerator

# Force UTF-8 stdout/stderr so the sub-agents' Arabic print() statements never
# crash on Windows (cp1252 console). Without this, printing an Arabic dish name
# raises UnicodeEncodeError and kills the whole process mid-stream → the browser
# sees a "network error". Must run before any agent module prints.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
from agent1_scout.discovery import geocode_location
from .runner import resume_run, start_run

app = FastAPI(title="Food Pilot Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    # Allow any localhost / 127.0.0.1 port during development (the web UI may run
    # on 3000, 3100, etc.). The browser talks to this bridge directly for SSE.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _warm_rag() -> None:
    """Load the RAG model + ChromaDB at startup (when RAM is freshest) instead of
    lazily on the first calorie request. If it fails, the bridge still serves —
    RAG just degrades — rather than crashing mid-conversation.

    NOTE: this model is ~1.1GB; loading needs a few GB of free RAM. If the
    process is killed here, close other apps (browser tabs) to free memory.
    """
    if not config.has_azure_openai():
        print("[startup] Azure OpenAI not configured — skipping RAG warmup.")
        return
    try:
        print("[startup] Warming up orchestrator + RAG (model + ChromaDB)…", flush=True)
        # Importing the orchestrator builds the RAG pipeline + classifier LLM once
        # at startup (when RAM is freshest) instead of on the first message.
        import orchestrator  # noqa: F401

        print("[startup] Orchestrator + RAG ready ✅", flush=True)
    except Exception as exc:  # noqa: BLE001 — never block startup on RAG
        print(f"[startup] Warmup failed (will retry on demand): {exc}", flush=True)


class ChatRequest(BaseModel):
    thread_id: str
    query: str
    location: str | None = None
    lat: float | None = None
    lon: float | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    resume: dict[str, Any]


def _sse(generator: AsyncGenerator[dict, None]) -> StreamingResponse:
    """Wrap an AgentEvent async generator as a text/event-stream response."""

    async def event_stream() -> AsyncGenerator[bytes, None]:
        async for event in generator:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
        yield b"data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _resolve_coords(req: ChatRequest) -> tuple[str, dict]:
    """Resolve a (location_text, {lat, lon}) pair from the request."""
    location = req.location or "Cairo, Egypt"
    if req.lat is not None and req.lon is not None:
        return location, {"lat": req.lat, "lon": req.lon}

    coords = geocode_location(location)
    if coords is None:
        # Fall back to central Cairo so the demo still works.
        return location, {"lat": 30.0444, "lon": 31.2357}
    return location, {"lat": coords.lat, "lon": coords.lon}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "azure_openai": config.has_azure_openai(),
        "apify": bool(config.APIFY_API_TOKEN),
        "tavily": bool(config.TAVILY_API_KEY),
        "tracing": config.tracing_enabled(),
    }


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    location, coords = _resolve_coords(req)
    return _sse(start_run(req.thread_id, req.query, location, coords))


@app.post("/resume")
async def resume(req: ResumeRequest) -> StreamingResponse:
    return _sse(resume_run(req.thread_id, req.resume))
