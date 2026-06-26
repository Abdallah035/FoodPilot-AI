"""Language detection + translation so chat output matches the user's language.

The user may write in Egyptian Arabic, English, or a mix. We:
  - detect the DOMINANT language of their query (`detect_lang`), and
  - translate arbitrary UI strings and scraped menu data into that language
    (`translate` for one string, `translate_many` for a batch).

Everything is best-effort: if Groq is unavailable or a call fails we return the
ORIGINAL text rather than crash. Results are cached per (lang, text) for the
process lifetime so repeated UI strings cost one call at most.
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import config

# language code -> human name used in the translation prompt
_LANG_NAMES = {
    "ar": "Egyptian Arabic",
    "en": "English",
}


def _llm():
    from langchain_groq import ChatGroq

    return ChatGroq(model=config.GROQ_MODEL, temperature=0, api_key=config.GROQ_API_KEY)


def _arabic_ratio(text: str) -> float:
    """Fraction of letters that are Arabic (cheap, offline heuristic)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(1 for c in letters if "؀" <= c <= "ۿ")
    return arabic / len(letters)


def detect_lang(text: str) -> str:
    """Return the dominant language code ('ar' or 'en') for `text`.

    Uses a script-based heuristic: if most letters are Arabic, the dominant
    language is Arabic. This handles mixed input by majority, with no LLM call.
    """
    return "ar" if _arabic_ratio(text or "") >= 0.5 else "en"


def is_rtl(lang: str) -> bool:
    return lang == "ar"


@lru_cache(maxsize=2048)
def _translate_cached(lang: str, text: str) -> str:
    if not text or not text.strip():
        return text
    if lang == "en":
        return text  # source UI text is authored in English
    if not config.has_groq():
        return text

    target = _LANG_NAMES.get(lang, lang)
    prompt = (
        f"Translate the following text into {target}. "
        "Keep it natural and concise. Preserve numbers, prices, and proper "
        "names. Reply with ONLY the translation, no quotes, no explanation.\n\n"
        f"{text}"
    )
    try:
        resp = _llm().invoke(prompt)
    except Exception:
        return text
    out = resp.content if hasattr(resp, "content") else str(resp)
    out = str(out).strip()
    return out or text


def translate(text: str, lang: str) -> str:
    """Translate one string into `lang` (cached). Returns original on failure."""
    return _translate_cached(lang, text or "")


def translate_many(texts: list[str], lang: str) -> list[str]:
    """Translate a list of strings into `lang` in a single LLM call.

    Falls back to per-item (cached) translation if the batch call fails, and to
    the original text if Groq is unavailable.
    """
    if not texts:
        return []
    if lang == "en" or not config.has_groq():
        return list(texts)

    target = _LANG_NAMES.get(lang, lang)
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(texts))
    prompt = (
        f"Translate each numbered line into {target}. "
        "Keep translations natural and concise. Preserve numbers, prices, and "
        "proper names. Return ONLY a JSON array of strings, in the same order, "
        "same length, no extra commentary.\n\n"
        f"{numbered}"
    )
    try:
        resp = _llm().invoke(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        start, end = str(raw).find("["), str(raw).rfind("]")
        arr = json.loads(str(raw)[start : end + 1])
        if isinstance(arr, list) and len(arr) == len(texts):
            return [str(x) for x in arr]
    except Exception:
        pass
    # fallback: per-item (still cached)
    return [translate(t, lang) for t in texts]
