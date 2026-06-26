"""Root configuration for Food Pilot.

This is the only module that reads environment variables. Other packages should
import settings or helpers from here instead of calling load_dotenv()/getenv().
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _clean_azure_endpoint(value: str | None) -> str:
    endpoint = (value or "").strip().rstrip("/")
    if endpoint.endswith("/openai/v1"):
        endpoint = endpoint[: -len("/openai/v1")]
    return endpoint.rstrip("/")


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# LLM provider: Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = _clean_azure_endpoint(os.getenv("AZURE_OPENAI_ENDPOINT"))
AZURE_OPENAI_DEPLOYMENT_NAME = (
    os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    or os.getenv("AZURE_OPENAI_DEPLOYMENT")
)
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# External tools
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Tracing
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "food-pilot")
LANGSMITH_TRACING = env_flag("LANGSMITH_TRACING")

# Scoring: max search radius in km (used to normalise proximity)
MAX_DISTANCE_KM = float(os.getenv("MAX_DISTANCE_KM", "10"))

# Live-test gates
RUN_APIFY = env_flag("RUN_APIFY")
RUN_DEALS = env_flag("RUN_DEALS")
RUN_LIVE = env_flag("RUN_LIVE")
RUN_TALABAT = env_flag("RUN_TALABAT")
RUN_TAVILY = env_flag("RUN_TAVILY")
RUN_AZURE_EST = env_flag("RUN_AZURE_EST")
RUN_TRACE = env_flag("RUN_TRACE")


if LANGSMITH_TRACING and not LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"


def has_azure_openai() -> bool:
    return all(
        [
            AZURE_OPENAI_API_KEY,
            AZURE_OPENAI_ENDPOINT,
            AZURE_OPENAI_DEPLOYMENT_NAME,
            AZURE_OPENAI_API_VERSION,
        ]
    )


def require_azure_openai() -> None:
    missing = [
        name
        for name, value in {
            "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
            "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
            "AZURE_OPENAI_DEPLOYMENT_NAME": AZURE_OPENAI_DEPLOYMENT_NAME,
            "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
        }.items()
        if not value
    ]
    if missing:
        raise EnvironmentError(
            "Azure OpenAI configuration is incomplete. Missing: " + ", ".join(missing)
        )


def get_azure_openai_llm(temperature: float = 0.0):
    require_azure_openai()

    from langchain_openai import AzureChatOpenAI

    return AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        openai_api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        temperature=temperature,
    )


def tracing_enabled() -> bool:
    """True when LangSmith tracing is switched on and a key is present."""
    return LANGSMITH_TRACING and bool(LANGSMITH_API_KEY)
