"""Shared configuration: loads .env once and exposes settings."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# LLM (Groq)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Tools
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Tracing
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "food-pilot")

# Scoring: max search radius in km (used to normalise proximity)
MAX_DISTANCE_KM = float(os.getenv("MAX_DISTANCE_KM", "10"))


LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "").lower() == "true"

if LANGSMITH_TRACING and not LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def has_groq() -> bool:
    return bool(GROQ_API_KEY)


def tracing_enabled() -> bool:
    """True when LangSmith tracing is switched on and a key is present."""
    return LANGSMITH_TRACING and bool(LANGSMITH_API_KEY)
