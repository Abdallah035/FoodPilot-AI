"""FastAPI bridge that exposes the Food Pilot multi-agent pipeline to the web UI.

The browser (web/) talks SSE to this bridge; the bridge drives the existing
LangGraph Scout graph + post-Scout pipeline and translates graph state into the
event protocol the frontend consumes (see web/src/lib/types.ts `AgentEvent`).
"""
