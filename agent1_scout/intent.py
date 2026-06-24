"""Task 2 — Intent parsing.

Extract the core food entity (and an optional budget) from a free-text craving.
Supports **Egyptian Arabic and English**, e.g.:
    - "I'm craving a good burger"      -> burger
    - "عايز كفتة"                       -> كفتة
    - "أرخص بيتزا"                       -> بيتزا, budget "$"

Uses the Groq LLM with structured output. There is no heuristic fallback: a
keyword stripper cannot parse Arabic reliably and risks wrong / double-meaning
results, so we fail loudly if the LLM is unavailable.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from . import config


class Intent(BaseModel):
    """Structured result of parsing a user craving."""

    food_entity: str = Field(
        description="the core food the user wants, in the user's own language "
        "(e.g. 'burger', 'كفتة', 'pizza')"
    )
    budget: Optional[str] = Field(
        default=None,
        description="price level the user implies: '$' (cheap), '$$' (mid), "
        "'$$$' (fancy), or null if unclear",
    )


_SYSTEM = (
    "You extract structured intent from a person's food craving. "
    "The user may write in Egyptian Arabic or English. "
    "Return the core food as `food_entity` in the SAME language the user used "
    "(do not translate). "
    "Set `budget` to '$' if they imply cheap (e.g. 'cheap', 'رخيص', 'أرخص'), "
    "'$$$' if they imply fancy/expensive (e.g. 'fancy', 'فخم'), '$$' for mid, "
    "or null if no budget is implied."
)


def parse_intent(user_query: str) -> Intent:
    """Parse a craving (Arabic or English) into an `Intent` using Groq.

    Raises if no Groq key is configured or the call fails — we do not guess.
    """
    if not config.has_groq():
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env to parse intents."
        )

    from langchain_groq import ChatGroq

    llm = ChatGroq(model=config.GROQ_MODEL, temperature=0, api_key=config.GROQ_API_KEY)
    structured = llm.with_structured_output(Intent)
    return structured.invoke(
        [
            ("system", _SYSTEM),
            ("human", user_query),
        ]
    )
