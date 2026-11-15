"""Explainable sentiment: lexicon cues + rules. Returns label, confidence, evidence and rule ids.

Rules (ids stored in prediction.rules_fired):
  LEX        polarity cues found                 NEGATION   negator within 3 tokens before (or 2 after, hi/te/Hinglish)
  INTENSIFIER cue weight x1.5                    CONTRAST   'but/pero/lekin/kani' splits opposite polarities -> mixed
  BOTH_POLARITIES opposite cues, no marker       SARCASM    sarcasm cue + complaint -> negative, low confidence
  MIXED_CUE 'mixed feelings' -> mixed   CONTRAST_ONE_SIDED marker but one polarity -> low conf.
  AMBIGUOUS  hedging cue -> neutral, low conf.   NEUTRAL_CUE explicit neutral phrase   NO_CUES nothing matched
  CODE_MIXED / LANG_MISMATCH  confidence -0.1
"""
from __future__ import annotations

from functools import lru_cache

from . import lexicon as L
from .matcher import Matcher, tokens_after, tokens_before

POST_NEGATION_LANGS = {"hi", "te", "hi-Latn"}     # negator follows the word: "achha nahi", "अच्छा नहीं"


@lru_cache(maxsize=None)
def _lang(lang: str):
    lexes = L.LEXICONS.get(lang, L.LEXICONS["en"])
    merged = {k: [t for lx in lexes for t in L.terms(lx[k])] for k in lexes[0]}
    return {
        "cues": Matcher({"neu": merged["neu"], "pos": merged["pos"], "neg": merged["neg"]}),
        "contrast": Matcher({"c": merged["contrast"]}),
        "sarcasm": Matcher({"s": merged["sarcasm"]}),
        "ambig": Matcher({"a": merged["ambig"]}),
        "mixed": Matcher({"m": merged["mixed"]}),
        "negators": set(merged["negators"]), "intens": set(merged["intens"]),
    }


def classify(text: str, lang: str, code_mixed: bool = False, lang_mismatch: bool = False) -> dict:
    lx = _lang(lang)
    low = text.lower().replace("’", "'")
    rules, evidence = set(), []
    bounds = [m.start for m in lx["contrast"].find(low)]
    pos = neg = 0.0
    clause_pol: dict[int, set[str]] = {}
    found = lx["cues"].find(low)
    for i, m in enumerate(found):
        # negation/intensifier window: same sentence, never inside another matched cue
        left = max(found[i - 1].end if i else 0, max((low.rfind(c, 0, m.start) for c in ".!?;,।"), default=-1) + 1)
        right = found[i + 1].start if i + 1 < len(found) else len(low)
        stop = min([j for j in (low.find(c, m.end, right) for c in ".!?;,।") if j != -1], default=right)
        if m.kind == "neu":
            evidence.append("~" + m.term)
            rules.add("NEUTRAL_CUE")
            continue
        w, pol = 1.0, m.kind
        before = tokens_before(low[left:m.start], len(low[left:m.start]), 3)
        after = tokens_after(low[m.end:stop], 0, 2) if lang in POST_NEGATION_LANGS else []
        if any(t in lx["intens"] for t in before[-1:]):
            w, _ = 1.5, rules.add("INTENSIFIER")
        if any(t in lx["negators"] for t in before + after):
            pol = "neg" if pol == "pos" else "pos"
            w = 0.6 if pol == "pos" else w        # "not bad" is weak praise
            rules.add("NEGATION")
            evidence.append(f"¬{m.term}")
        else:
            evidence.append(("+" if pol == "pos" else "-") + m.term)
        clause = sum(1 for b in bounds if b < m.start)
        clause_pol.setdefault(clause, set()).add(pol)
        pos, neg = (pos + w, neg) if pol == "pos" else (pos, neg + w)
    if pos or neg:
        rules.add("LEX")

    sarc = lx["sarcasm"].find(low)
    strong_sarc = [s for s in sarc if not s.term.endswith(",")]
    ambig = lx["ambig"].find(low)
    contrast = len(clause_pol) > 1 and any("pos" in p for p in clause_pol.values()) and \
        any("neg" in p for p in clause_pol.values())

    if strong_sarc or (sarc and neg):
        label, conf = "negative", 0.55
        rules.add("SARCASM")
        evidence += ["!" + s.term for s in sarc]
    elif ambig and not (pos and neg):
        label, conf = "neutral", 0.45
        rules.add("AMBIGUOUS")
        evidence += ["?" + a.term for a in ambig]
    elif mixed_cue := lx["mixed"].find(low):
        label, conf = "mixed", 0.8
        rules.add("MIXED_CUE")
        evidence += ["±" + m.term for m in mixed_cue]
    elif pos and neg:
        label = "mixed"
        conf = 0.8 if contrast else 0.55
        rules.add("CONTRAST" if contrast else "BOTH_POLARITIES")
    elif pos or neg:
        label = "positive" if pos else "negative"
        conf = 0.6 + 0.1 * min(pos + neg, 3.0)
        if bounds:                                  # 'but' with only one polar side: probably mixed, unsure
            conf = 0.55
            rules.add("CONTRAST_ONE_SIDED")
        if "NEGATION" in rules and pos and not neg:
            conf = 0.6                              # litotes ("not bad") is weak evidence
    elif "NEUTRAL_CUE" in rules:
        label, conf = "neutral", 0.8
    else:
        label, conf = "neutral", 0.5
        rules.add("NO_CUES")
    if code_mixed:
        conf -= 0.1
        rules.add("CODE_MIXED")
    if lang_mismatch:
        conf -= 0.1
        rules.add("LANG_MISMATCH")
    return {"sentiment": label, "confidence": round(max(0.05, min(conf, 0.95)), 3),
            "evidence": evidence, "rules": sorted(rules)}


