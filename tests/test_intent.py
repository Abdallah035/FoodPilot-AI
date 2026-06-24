"""Task 2 — unit tests for intent parsing (Groq, Arabic + English).

These call the real Groq API and are skipped automatically if GROQ_API_KEY
is not configured.
"""

import pytest

from agent1_scout import config
from agent1_scout.intent import Intent, parse_intent

requires_groq = pytest.mark.skipif(
    not config.has_groq(), reason="GROQ_API_KEY not set"
)


@requires_groq
def test_english_burger():
    intent = parse_intent("I'm craving a good burger")
    assert isinstance(intent, Intent)
    assert "burger" in intent.food_entity.lower()


@requires_groq
def test_english_cheap_pizza_budget():
    intent = parse_intent("cheap pizza near me")
    assert "pizza" in intent.food_entity.lower()
    assert intent.budget == "$"


@requires_groq
def test_egyptian_arabic_kofta():
    intent = parse_intent("عايز كفتة")
    # food entity should stay in Arabic and contain the kofta root
    assert "كفت" in intent.food_entity


@requires_groq
def test_egyptian_arabic_cheap():
    intent = parse_intent("أرخص بيتزا")
    assert "بيتزا" in intent.food_entity or "pizza" in intent.food_entity.lower()
    assert intent.budget == "$"
