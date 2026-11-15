"""Analysis rules (no DB needed): redaction, language detection, sentiment rules, themes, routing, rules hash."""
import pandas as pd
import pytest

from voicelens.analyze.normalize import detect_language, redact
from voicelens.analyze.route import route
from voicelens.analyze.run import rules_hash
from voicelens.analyze.sentiment import classify
from voicelens.analyze.themes import ThemeClassifier


def test_redaction_masks_pii_but_not_products():
    text = "Orbix Router broke. Reach me at asha.rao12@example.com or +1-555-0142. - Asha Rao"
    out, n = redact(text, {"Asha Rao"})
    assert "[EMAIL]" in out and "[PHONE]" in out and "[NAME]" in out and "Orbix Router" in out
    assert n == {"email": 1, "phone": 1, "name": 1}


@pytest.mark.parametrize("text,lang", [("రీఫండ్ బాగాలేదు.", "te"), ("ऐप से मैं खुश हूँ।", "hi"),
                                       ("El precio de la app es muy alto.", "es"),
                                       ("Login ka bahut bura haal hai yaar.", "hi-Latn"), ("The app is great.", "en")])
def test_language_detection(text, lang):
    assert detect_language(text) == lang


@pytest.mark.parametrize("text,lang,label,rule", [
    ("The verification code never arrives. Very disappointed.", "en", "negative", "LEX"),
    ("The setup was not bad at all.", "en", "positive", "NEGATION"),
    ("Delivery was quick, but the refund was rejected.", "en", "mixed", "CONTRAST"),
    ("Fantastic, the price went up again without warning.", "en", "negative", "SARCASM"),
    ("Not sure how I feel about the payment yet.", "en", "neutral", "AMBIGUOUS"),
    ("Product quality achha nahi hai.", "hi-Latn", "negative", "NEGATION"),
    ("బిల్లింగ్ తో సంతోషం, కానీ డెలివరీ సమయం తో చాలా ఇబ్బంది.", "te", "mixed", "CONTRAST"),
    ("La configuración inicial es normal, nada especial.", "es", "neutral", "NEUTRAL_CUE"),
])
def test_sentiment_rules(text, lang, label, rule):
    r = classify(text, lang)
    assert r["sentiment"] == label and rule in r["rules"] and 0 <= r["confidence"] <= 1, r


def test_negation_does_not_cross_sentences():
    r = classify("The code never arrives. Very disappointed.", "en")
    assert "NEGATION" not in r["rules"] and r["sentiment"] == "negative"


THEMES = pd.DataFrame([
    {"theme_id": "THEME-000001", "code": "delivery", "parent_theme_id": None, "keywords": "delivery|courier"},
    {"theme_id": "THEME-000011", "code": "late_delivery", "parent_theme_id": "THEME-000001", "keywords": "late|delayed"},
    {"theme_id": "THEME-000009", "code": "refunds", "parent_theme_id": None, "keywords": "refund"},
])


def test_themes_child_beats_parent_one_per_clause_and_products_masked():
    tc = ThemeClassifier(THEMES, ["ParcelPal Same-Day"])
    assert tc.classify("The delivery was delayed again.")[0] == ["THEME-000011"]
    assert tc.classify("The delivery was fine, but the refund never came.")[0] == ["THEME-000001", "THEME-000009"]
    assert tc.classify("ParcelPal Same-Day is my provider.")[0] == []


def test_routing_reasons():
    sure = {"sentiment": "positive", "confidence": 0.9, "rules": ["LEX"]}
    assert route(sure, 1, 0.9, False) == ("auto", "")
    assert route(sure, 0, 0.1, True) == ("review", "NO_THEME|RATING_CONFLICT|LABEL_CONFLICT")
    sarcastic = {"sentiment": "negative", "confidence": 0.55, "rules": ["SARCASM"]}
    assert route(sarcastic, 1, None, False) == ("review", "LOW_CONFIDENCE|SARCASM")


def test_rules_hash_is_stable():
    assert rules_hash() == rules_hash() and len(rules_hash()) == 12
