"""Stage 2 - normalize: one curated feedback table across channels, PII redacted, language detected.
Quarantined rows (validation disposition QUARANTINE on the item itself) are excluded. The `tags` column is never
selected, so nothing written there can reach the model (leakage guard by construction)."""
from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import Engine

from . import lexicon as L

FEEDBACK_SQL = """
SELECT 'review' AS source_type, r.review_id AS source_id, r.customer_id, r.product_id, r.channel_id,
       'review' AS channel_type, r.posted_at AS event_at, (r.rating - 1) / 4.0 AS score_norm, r.language, r.text
FROM raw.review r
UNION ALL
SELECT 'survey_response', s.response_id, s.customer_id, s.product_id, v.channel_id, 'survey', s.submitted_at,
       s.score / 10.0, s.language, s.text
FROM raw.survey_response s JOIN raw.survey v USING (survey_id)
UNION ALL
SELECT 'support_message', m.message_id, t.customer_id, t.product_id, t.channel_id, 'support', m.sent_at,
       NULL, m.language, m.text
FROM raw.support_message m JOIN raw.support_ticket t USING (ticket_id)
WHERE m.sender = 'customer'
"""
QUARANTINED_SQL = """SELECT DISTINCT source_type, source_id FROM app.data_exception
WHERE disposition = 'QUARANTINE' AND table_name = source_type"""

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
NAME_CANDIDATE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")
TELUGU, DEVANAGARI = re.compile(r"[ఀ-౿]"), re.compile(r"[ऀ-ॿ]")
WORD = re.compile(r"[a-záéíóúñü]+")
ES_M, HG_M = set(L.terms(L.ES_MARKERS)), set(L.terms(L.HINGLISH_MARKERS))


def redact(text: str, names: set[str]) -> tuple[str, dict[str, int]]:
    counts = {"email": 0, "phone": 0, "name": 0}

    def sub(kind, token):
        def f(m):
            if kind == "name" and m.group(0) not in names:
                return m.group(0)
            counts[kind] += 1
            return token
        return f
    text = EMAIL.sub(sub("email", "[EMAIL]"), text)
    text = PHONE.sub(sub("phone", "[PHONE]"), text)
    text = NAME_CANDIDATE.sub(sub("name", "[NAME]"), text)
    return text, counts


def detect_language(text: str) -> str:
    if TELUGU.search(text):
        return "te"
    if DEVANAGARI.search(text):
        return "hi"
    words = WORD.findall(text.lower())
    es, hg = sum(w in ES_M for w in words), sum(w in HG_M for w in words)
    if es >= 2 and es > hg:
        return "es"
    if hg >= 2:
        return "hi-Latn"
    return "en"


def build_feedback(engine: Engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """-> (feedback items incl. text columns, PII findings [source_type, source_id, detail])."""
    with engine.connect() as c:
        fb = pd.read_sql(FEEDBACK_SQL, c)
        q = pd.read_sql(QUARANTINED_SQL, c)
        names = set(pd.read_sql("SELECT display_name FROM raw.customer", c)["display_name"])
    fb = fb.merge(q.assign(_q=1), on=["source_type", "source_id"], how="left")
    fb = fb[fb["_q"].isna()].drop(columns="_q").sort_values(["source_type", "source_id"]).reset_index(drop=True)
    red = [redact(t, names) for t in fb["text"]]
    fb["redacted_text"] = [r[0] for r in red]
    fb["pii_count"] = [sum(r[1].values()) for r in red]
    fb["language_detected"] = fb["text"].map(detect_language)
    fb["code_mixed"] = (fb["language_detected"] == "hi-Latn").astype(int)
    fb["event_at"] = pd.to_datetime(fb["event_at"])
    fb["week_start"] = (fb["event_at"] - pd.to_timedelta(fb["event_at"].dt.weekday, unit="D")).dt.date
    pii = pd.DataFrame([{"source_type": st, "source_id": sid,
                         "detail": "redacted " + ", ".join(f"{n} {k}" for k, n in r[1].items() if n)}
                        for st, sid, r in zip(fb["source_type"], fb["source_id"], red) if sum(r[1].values())],
                       columns=["source_type", "source_id", "detail"])
    return fb, pii
