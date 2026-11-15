"""Build all tables in parent -> child order from ONE seeded numpy Generator.

Order: product, channel, theme, customer, survey  ->  review, survey_response, support_ticket,
support_message, ticket_status_event  ->  gold labels + eval split  ->  input tags (sentiment_label,
feedback_theme)  ->  edge cases (edge_cases.py).  Derived values (ratings from sentiment, survey status,
ticket status / closed_at) are computed from source records, never drawn independently.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from . import world
from .config import (CUSTOMER_SINCE, INPUT_TAG_SHARE, REFERENCE_DATE, SENTIMENTS, WINDOW_END,
                     WINDOW_START, Volumes, volumes)
from .taxonomy import (APPLICABLE_THEMES, CHANNELS, FIRST_NAMES, LANGUAGE_WEIGHTS, LANGUAGES, LAST_NAMES,
                       PRODUCTS, REGION_BY_LANGUAGE, SEGMENT_WEIGHTS, SEGMENTS, THEME_EFFECTIVE_FROM,
                       THEME_ID_BY_CODE, THEMES)
from .templates import AGENT_REPLIES, render

CUTOFF = datetime.combine(REFERENCE_DATE, time())       # nothing happens at/after "today"
DT_FMT = "%Y-%m-%d %H:%M:%S"
PRODUCT_BY_ID = {p[0]: p for p in PRODUCTS}
TAG_VALUES = ("", "verified_purchase", "promo", "beta_user")
TAG_WEIGHTS = np.array([0.55, 0.30, 0.10, 0.05])

# Derived-value rule: rating / NPS score range implied by the text's sentiment (value within range from rng).
RATING_RANGE = {"positive": (4, 5), "negative": (1, 2), "neutral": (3, 3), "mixed": (2, 4)}
SCORE_RANGE = {"positive": (9, 10), "negative": (0, 6), "neutral": (7, 8), "mixed": (5, 8)}


# ------------------------------------------------------------------ helpers
def _rand_dt(rng: np.random.Generator, start: date, end: date) -> datetime:
    """Uniform datetime between start 00:00 and end 23:59:59 (inclusive days)."""
    days = (end - start).days + 1
    return datetime.combine(start, time()) + timedelta(seconds=int(rng.integers(days * 86_400)))


def _choice(rng: np.random.Generator, seq, p=None):
    return seq[int(rng.choice(len(seq), p=p))]


def _fmt(dt) -> str | None:
    return None if dt is None else dt.strftime(DT_FMT)


class _Ctx:
    def __init__(self, rng: np.random.Generator, vol: Volumes):
        self.rng, self.vol = rng, vol
        self.gold: list[dict] = []          # one row per labelled feedback item (ground truth)


def _feedback(ctx: _Ctx, channel_type: str, at: datetime, language: str, product_id: str | None = None,
              forced: tuple | None = None) -> dict:
    """Pick product/theme/sentiment (baseline or incident-caused) and render text. Labels come from the template."""
    rng, d = ctx.rng, at.date()
    if product_id is None:
        product_id = PRODUCTS[int(rng.choice(len(PRODUCTS), p=world.product_weights(channel_type, d)))][0]
    _, pname, category, _ = PRODUCT_BY_ID[product_id]
    applicable = APPLICABLE_THEMES[category]
    override = forced or world.incident_override(rng, product_id, channel_type, d)
    if override:
        incident_id, theme, sentiment, phase = override
    else:
        incident_id, phase = None, None
        sentiment = SENTIMENTS[int(rng.integers(4))]
        theme = _choice(rng, applicable)
    second = _choice(rng, [t for t in applicable if t != theme]) if sentiment == "mixed" else None
    item = render(rng, language, sentiment, theme, pname, second)
    item.update(product_id=product_id, incident_id=incident_id, incident_phase=phase, at=at)
    return item


def _gold(ctx: _Ctx, source_type: str, source_id: str, item: dict) -> None:
    ctx.gold.append({
        "source_type": source_type, "source_id": source_id, "sentiment": item["sentiment"],
        "theme_ids": "|".join(THEME_ID_BY_CODE[t] for t in item["themes"]),
        "style": item["style"], "language": item["language"], "template_id": item["template_id"],
        "incident_id": item["incident_id"], "incident_phase": item["incident_phase"],
        "product_id": item["product_id"], "_at": item["at"],
    })


# ------------------------------------------------------------------ master data
def _masters() -> dict[str, pd.DataFrame]:
    product = pd.DataFrame([{"product_id": p, "name": n, "category": c, "launched_at": l.isoformat(),
                             "status": "ACTIVE"} for p, n, c, l in PRODUCTS])
    channel = pd.DataFrame([{"channel_id": c, "name": n, "channel_type": t} for c, n, t in CHANNELS])
    theme = pd.DataFrame([{"theme_id": i, "code": c, "name": n, "parent_theme_id": par, "keywords": k,
                           "severity_weight": s, "effective_from": THEME_EFFECTIVE_FROM.isoformat(),
                           "effective_to": None} for i, c, n, par, k, s in THEMES])
    return {"product": product, "channel": channel, "theme": theme}


def _customers(ctx: _Ctx) -> pd.DataFrame:
    rng, rows = ctx.rng, []
    span = (WINDOW_START - CUSTOMER_SINCE).days
    for i in range(1, ctx.vol.customers + 1):
        lang = _choice(rng, LANGUAGES, p=np.array(LANGUAGE_WEIGHTS))
        first, last = _choice(rng, FIRST_NAMES), _choice(rng, LAST_NAMES)
        rows.append({
            "customer_id": f"CUST-{i:06d}", "display_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i}@example.com",
            "phone": f"+1-555-01{int(rng.integers(100)):02d}",
            "segment": _choice(rng, SEGMENTS, p=np.array(SEGMENT_WEIGHTS)),
            "region": _choice(rng, REGION_BY_LANGUAGE[lang]), "preferred_language": lang,
            "created_at": (CUSTOMER_SINCE + timedelta(days=int(rng.integers(span)))).isoformat(),
        })
    return pd.DataFrame(rows)


def _surveys(ctx: _Ctx) -> pd.DataFrame:
    """Staggered survey windows covering the feedback window; status derived from dates vs REFERENCE_DATE."""
    rng, n, rows = ctx.rng, ctx.vol.surveys, []
    span = (WINDOW_END - WINDOW_START).days - 35
    specs = []
    for k in range(n):
        opens = WINDOW_START + timedelta(days=round(k * span / max(1, n - 1)) if n > 1 else 0)
        closes = opens + timedelta(days=int(rng.integers(56, 91)))
        product = PRODUCTS[int(rng.integers(len(PRODUCTS)))][0] if rng.random() < 0.6 else None
        specs.append((opens, closes, _choice(rng, ["CHAN-01", "CHAN-02"]), product))
    specs.append((date(2026, 10, 15), date(2026, 11, 15), "CHAN-01", None))   # a future DRAFT survey
    for i, (opens, closes, chan, product) in enumerate(specs, start=1):
        status = "DRAFT" if opens > REFERENCE_DATE else ("CLOSED" if closes < REFERENCE_DATE else "OPEN")
        label = PRODUCT_BY_ID[product][1] if product else "General"
        rows.append({"survey_id": f"SUR-2026-{i:06d}", "name": f"{label} feedback survey {opens:%b %Y}",
                     "channel_id": chan, "product_id": product, "opens_at": opens.isoformat(),
                     "closes_at": closes.isoformat(), "status": status})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ feedback
def _reviews(ctx: _Ctx, cust: pd.DataFrame) -> pd.DataFrame:
    rng, n = ctx.rng, ctx.vol.reviews
    times = sorted(_rand_dt(rng, WINDOW_START, WINDOW_END) for _ in range(n))
    rows = []
    for i, at in enumerate(times, start=1):
        c = int(rng.integers(len(cust)))
        item = _feedback(ctx, "review", at, cust.at[c, "preferred_language"])
        rid = f"REV-2026-{i:06d}"
        lo, hi = RATING_RANGE[item["sentiment"]]
        rows.append({"review_id": rid, "customer_id": cust.at[c, "customer_id"], "product_id": item["product_id"],
                     "channel_id": _choice(rng, ["CHAN-03", "CHAN-04"]), "rating": int(rng.integers(lo, hi + 1)),
                     "text": item["text"], "language": item["language"], "posted_at": _fmt(at),
                     "tags": _choice(rng, TAG_VALUES, p=TAG_WEIGHTS)})
        _gold(ctx, "review", rid, item)
    return pd.DataFrame(rows)


def _responses(ctx: _Ctx, cust: pd.DataFrame, surveys: pd.DataFrame) -> pd.DataFrame:
    rng, n = ctx.rng, ctx.vol.responses
    live = surveys[surveys["status"] != "DRAFT"].reset_index(drop=True)
    spans = []
    for _, s in live.iterrows():
        o, c = date.fromisoformat(s["opens_at"]), min(date.fromisoformat(s["closes_at"]), WINDOW_END)
        spans.append((o, c))
    w = np.array([(c - o).days + 1 for o, c in spans], dtype=float)
    picks = rng.choice(len(live), size=n, p=w / w.sum())
    draws = sorted((int(k), _rand_dt(rng, *spans[int(k)])) for k in picks)   # sorted by survey, then time
    used, counter, rows = set(), {}, []
    for k, at in draws:
        sid = live.at[k, "survey_id"]
        while True:                                   # one response per (customer, survey)
            c = int(rng.integers(len(cust)))
            if (c, sid) not in used:
                used.add((c, sid))
                break
        counter[sid] = counter.get(sid, 0) + 1
        rid = f"RESP-{sid}-{counter[sid]:03d}"
        pid = live.at[k, "product_id"]
        pid = None if pd.isna(pid) else pid            # general survey -> product sampled per response
        item = _feedback(ctx, "survey", at, cust.at[c, "preferred_language"], product_id=pid)
        lo, hi = SCORE_RANGE[item["sentiment"]]
        rows.append({"response_id": rid, "survey_id": sid, "customer_id": cust.at[c, "customer_id"],
                     "product_id": item["product_id"], "score": int(rng.integers(lo, hi + 1)),
                     "text": item["text"], "language": item["language"], "submitted_at": _fmt(at),
                     "tags": _choice(rng, TAG_VALUES, p=TAG_WEIGHTS)})
        _gold(ctx, "survey_response", rid, item)
    return pd.DataFrame(rows)


def _support(ctx: _Ctx, cust: pd.DataFrame):
    """Tickets -> messages -> status events. Status and closed_at are DERIVED from the event history."""
    rng, n = ctx.rng, ctx.vol.tickets
    times = sorted(_rand_dt(rng, WINDOW_START, WINDOW_END) for _ in range(n))
    tickets, messages, events = [], [], []
    for i, opened in enumerate(times, start=1):
        tid = f"TKT-2026-{i:06d}"
        c = int(rng.integers(len(cust)))
        lang = cust.at[c, "preferred_language"]
        first = _feedback(ctx, "support", opened, lang)
        # messages: alternate customer / agent, 1-30 h apart, never at/after the cutoff
        t, msg_times = opened, []
        for j in range(int(rng.integers(2, 7))):
            if j:
                t = t + timedelta(seconds=int(rng.integers(3_600, 30 * 3_600)))
            if t >= CUTOFF:
                break
            msg_times.append(t)
        for j, mt in enumerate(msg_times, start=1):
            mid = f"MSG-{tid}-{j:03d}"
            if j % 2 == 1:   # customer message: labelled feedback, same theme as the ticket
                if j == 1:
                    item = first
                else:
                    forced = None
                    if first["incident_id"]:
                        forced = (first["incident_id"], first["themes"][0], first["sentiment"], first["incident_phase"])
                    elif first["sentiment"] != "mixed":
                        forced = (None, first["themes"][0], SENTIMENTS[int(rng.integers(4))], None)
                    item = _feedback(ctx, "support", mt, lang, product_id=first["product_id"], forced=forced)
                messages.append({"message_id": mid, "ticket_id": tid, "sender": "customer", "text": item["text"],
                                 "language": lang, "sent_at": _fmt(mt)})
                _gold(ctx, "support_message", mid, item)
            else:
                messages.append({"message_id": mid, "ticket_id": tid, "sender": "agent",
                                 "text": _choice(rng, AGENT_REPLIES), "language": "en", "sent_at": _fmt(mt)})
        # lifecycle events: OPEN -> IN_PROGRESS -> RESOLVED [-> REOPENED -> IN_PROGRESS -> RESOLVED] -> CLOSED
        h = lambda lo, hi: timedelta(seconds=int(rng.integers(lo * 3_600, hi * 3_600)))
        in_prog = msg_times[1] if len(msg_times) > 1 else opened + h(1, 4)
        seq = [(None, "OPEN", "customer", opened), ("OPEN", "IN_PROGRESS", "agent", in_prog)]
        resolved = max(msg_times[-1], in_prog) + h(1, 24)
        seq.append(("IN_PROGRESS", "RESOLVED", "agent", resolved))
        if rng.random() < 0.10:
            reopened = resolved + h(24, 72)
            again = reopened + h(1, 6)
            resolved = again + h(24, 48)
            seq += [("RESOLVED", "REOPENED", "customer", reopened), ("REOPENED", "IN_PROGRESS", "agent", again),
                    ("IN_PROGRESS", "RESOLVED", "agent", resolved)]
        seq.append(("RESOLVED", "CLOSED", "system", resolved + timedelta(days=2)))
        seq = [e for e in seq if e[3] < CUTOFF]
        for frm, to, actor, at in seq:
            events.append({"ticket_id": tid, "from_status": frm, "to_status": to, "actor": actor, "event_at": _fmt(at)})
        closed = seq[-1][3] if seq[-1][1] == "CLOSED" else None
        tickets.append({"ticket_id": tid, "customer_id": cust.at[c, "customer_id"], "product_id": first["product_id"],
                        "channel_id": _choice(rng, ["CHAN-05", "CHAN-06"]), "opened_at": _fmt(opened),
                        "closed_at": _fmt(closed), "current_status": seq[-1][1]})
    ev = pd.DataFrame(events)
    ev.insert(0, "event_id", [f"TSE-{k:06d}" for k in range(1, len(ev) + 1)])
    return pd.DataFrame(tickets), pd.DataFrame(messages), ev


# ------------------------------------------------------------------ split + input tags
def _split_and_tags(ctx: _Ctx, gold: pd.DataFrame):
    """Stratified eval split (gold only) + source-system tags on a share of TRAIN items (input)."""
    rng = ctx.rng
    gold["split"] = "train"
    per = ctx.vol.eval_items // 4
    for s in SENTIMENTS:
        idx = gold.index[gold["sentiment"] == s].to_numpy()
        take = rng.choice(idx, size=min(per, len(idx)), replace=False)
        gold.loc[take, "split"] = "eval"
    train = gold.index[gold["split"] == "train"].to_numpy()
    tagged = np.sort(rng.choice(train, size=round(len(train) * INPUT_TAG_SHARE), replace=False))
    labels, themes = [], []
    for k, gi in enumerate(tagged, start=1):
        g = gold.loc[gi]
        at = _fmt(min(g["_at"] + timedelta(days=1), CUTOFF - timedelta(seconds=1)))
        labels.append({"label_id": f"LBL-{k:06d}", "source_type": g["source_type"], "source_id": g["source_id"],
                       "sentiment": g["sentiment"], "labeler": "source_system", "label_note": "",
                       "labeled_at": at})
        for th in g["theme_ids"].split("|"):
            themes.append({"source_type": g["source_type"], "source_id": g["source_id"], "theme_id": th,
                           "labeler": "source_system", "tagged_at": at})
    return pd.DataFrame(labels), pd.DataFrame(themes)


# ------------------------------------------------------------------ entry point
def build(scale: float, seed: int):
    """Return (input_tables, ground_truth_tables, volumes). Same (scale, seed) -> identical output."""
    from .edge_cases import inject   # local import keeps module graph simple

    rng = np.random.default_rng(seed)
    vol = volumes(scale)
    ctx = _Ctx(rng, vol)
    t = _masters()
    t["customer"] = _customers(ctx)
    t["survey"] = _surveys(ctx)
    t["review"] = _reviews(ctx, t["customer"])
    t["survey_response"] = _responses(ctx, t["customer"], t["survey"])
    t["support_ticket"], t["support_message"], t["ticket_status_event"] = _support(ctx, t["customer"])
    gold = pd.DataFrame(ctx.gold)
    t["sentiment_label"], t["feedback_theme"] = _split_and_tags(ctx, gold)

    anomalies = inject(rng, t, gold, vol.anomalies_per_type)

    incidents = []
    for inc in world.INCIDENTS:
        row = {k: inc[k] for k in ("incident_id", "name", "description", "product_id", "direction")}
        row["theme_id"] = THEME_ID_BY_CODE[inc["theme_code"]]
        row["onset_date"], row["end_date"] = inc["onset_date"].isoformat(), inc["end_date"].isoformat()
        for ch in ("support", "review", "survey"):
            start, _ = world.signal_window(inc, ch)
            row[f"lag_{ch}_days"] = (start - inc["onset_date"]).days
            row[f"{ch}_signal_start"] = start.isoformat()
        for k in ("volume_boost", "override_prob", "pre_onset_prob"):
            row[k] = inc[k]
        caused = gold[(gold["incident_id"] == inc["incident_id"]) & (gold["incident_phase"] == "post")]
        for st, col in (("support_message", "n_support_items"), ("review", "n_review_items"),
                        ("survey_response", "n_survey_items")):
            row[col] = int((caused["source_type"] == st).sum())
        incidents.append(row)

    gold = gold.drop(columns=["_at"]).sort_values(["source_type", "source_id"]).reset_index(drop=True)
    gt = {"labels": gold, "incidents": pd.DataFrame(incidents), "anomalies": anomalies}
    return t, gt, vol
