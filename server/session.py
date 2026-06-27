"""Per-thread session state for the SSE bridge.

Each browser conversation maps to one LangGraph thread. The Scout graph pauses
at two interrupts; we keep the compiled graph + its config so a later /resume
call can continue the same thread via `Command(resume=...)`.

A single shared MemorySaver checkpointer backs all threads. Swap it for a
persistent checkpointer (e.g. SqliteSaver) to survive restarts.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from agent1_scout.graph import build_graph


@dataclass
class Session:
    thread_id: str
    config: dict[str, Any]
    # The most recent scout payload once both interrupts are resolved.
    last_payload: dict[str, Any] | None = None


class SessionStore:
    """Thread-safe registry of conversations sharing one checkpointer + graph."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._checkpointer = MemorySaver()
        self._graph = build_graph(checkpointer=self._checkpointer)
        self._sessions: dict[str, Session] = {}

    @property
    def graph(self):
        return self._graph

    def get_or_create(self, thread_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(thread_id)
            if session is None:
                session = Session(
                    thread_id=thread_id,
                    config={"configurable": {"thread_id": thread_id}},
                )
                self._sessions[thread_id] = session
            return session

    def get(self, thread_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(thread_id)


# Module-level singleton used by the FastAPI app.
store = SessionStore()
