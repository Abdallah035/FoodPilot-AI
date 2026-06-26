"""Tests for language detection + translation passthrough (no LLM calls)."""

from agent1_scout import i18n


def test_detect_pure_languages():
    assert i18n.detect_lang("عايز كشري كويس") == "ar"
    assert i18n.detect_lang("I'm craving a good burger") == "en"


def test_detect_mixed_uses_dominant():
    # mostly Arabic letters -> ar
    assert i18n.detect_lang("عايز burger كويس جدا اوي") == "ar"
    # mostly English letters -> en
    assert i18n.detect_lang("I want كشري please right now") == "en"


def test_detect_empty_defaults_english():
    assert i18n.detect_lang("") == "en"
    assert i18n.detect_lang("12345 !!!") == "en"  # no letters


def test_is_rtl():
    assert i18n.is_rtl("ar") is True
    assert i18n.is_rtl("en") is False


def test_english_passthrough_no_llm():
    # English target never calls Groq; returns text unchanged
    assert i18n.translate("Pick a restaurant:", "en") == "Pick a restaurant:"
    assert i18n.translate_many(["a", "b"], "en") == ["a", "b"]


def test_empty_translate_passthrough():
    assert i18n.translate("", "ar") == ""
    assert i18n.translate_many([], "ar") == []
