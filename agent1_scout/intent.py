"""Task 2 — Intent parsing.

Extract the core food entity (and an optional budget) from a free-text craving.
Supports **Egyptian Arabic and English**, e.g.:
    - "I'm craving a good burger"      -> burger
    - "عايز كفتة"                       -> كفتة
    - "أرخص بيتزا"                       -> بيتزا, budget "$"

Uses Azure OpenAI with structured output. There is no heuristic fallback: a
keyword stripper cannot parse Arabic reliably and risks wrong / double-meaning
results, so we fail loudly if the LLM is unavailable.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

import config


class Intent(BaseModel):
    """Structured result of parsing a user craving."""

    food_entity: str = Field(
        description="the exact dish the user wants, in the user's own language "
        "(e.g. 'burger', 'كفتة', 'pizza'). Used later to match menu items/deals."
    )
    search_category: str = Field(
        default="",
        description="the RESTAURANT category/cuisine to search for on the map that "
        "SERVES this dish, in Arabic for Arabic input (e.g. 'كفتة'/'كباب'/'شيش' -> "
        "'مشويات'; 'بيتزا' -> 'بيتزا'; 'سوشي' -> 'سوشي'; 'برجر' -> 'برجر'; "
        "'كشري' -> 'كشري'; 'فراخ' -> 'مطعم فراخ'). This is what we type into the "
        "maps search, NOT a specific restaurant name."
    )
    budget: Optional[str] = Field(
        default=None,
        description="price level the user implies: '$' (cheap), '$$' (mid), "
        "'$$$' (fancy), or null if unclear",
    )


_SYSTEM = (
    "You extract structured intent from a person's food craving. "
    "The user may write in Egyptian Arabic or English. "
    "Return the exact dish as `food_entity` in the SAME language the user used "
    "(do not translate). "
    "Return `search_category`: the kind of RESTAURANT/cuisine to search for on a "
    "map that SERVES this dish — NOT a restaurant name, and NOT the dish itself "
    "when the dish wouldn't be a restaurant category. "
    "Examples (Arabic): 'كفتة'/'كباب'/'شيش طاووق'/'ريش' -> 'مشويات'; "
    "'فراخ مشوية' -> 'مشويات'; 'سمك'/'جمبري' -> 'مأكولات بحرية'; "
    "'كشري' -> 'كشري'; 'بيتزا' -> 'بيتزا'; 'برجر' -> 'برجر'; 'سوشي' -> 'سوشي'; "
    "'حلويات'/'كنافة' -> 'حلويات'. "
    "Examples (English): 'kofta'/'kebab' -> 'grill'; 'steak' -> 'steakhouse'; "
    "'shrimp' -> 'seafood'; 'pizza' -> 'pizza'. "
    "If the dish name IS itself a common restaurant category, you may reuse it. "
    "Set `budget` to '$' if they imply cheap (e.g. 'cheap', 'رخيص', 'أرخص'), "
    "'$$$' if they imply fancy/expensive (e.g. 'fancy', 'فخم'), '$$' for mid, "
    "or null if no budget is implied."
)


def parse_intent(user_query: str) -> Intent:
    """Parse a craving (Arabic or English) into an `Intent` using Azure OpenAI.

    Raises if Azure OpenAI is not configured or the call fails — we do not guess.
    """
    llm = config.get_azure_openai_llm(temperature=0)
    structured = llm.with_structured_output(Intent)
    return structured.invoke(
        [
            ("system", _SYSTEM),
            ("human", user_query),
        ]
    )
