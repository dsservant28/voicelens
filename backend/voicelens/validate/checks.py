"""Stage-1 ingest gate. Every check reads its rules from generate/contract.py (types, required, enums, ID patterns,
uniqueness, FKs, lifecycles) plus a few documented cross-table rules (dates, derived values, duplicates).
A failing row never crashes the run: it becomes a data_exception row with a disposition
  QUARANTINE -> excluded from analysis (row kept in the DB for audit)    FLAG -> kept, shown on the data-quality page.
This module reads ONLY the input files (csv/), never ground_truth/.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pandas as pd

from ..generate import contract as C
from ..generate.config import REFERENCE_DATE, WINDOW_END, WINDOW_START

Tables = dict[str, pd.DataFrame]
FEEDBACK_TS = {"review": ("review_id", "posted_at"), "survey_response": ("response_id", "submitted_at"),
               "support_message": ("message_id", "sent_at")}
CHANNEL_TYPE_OF = {"survey": "survey", "review": "review", "support_ticket": "support"}


@dataclass(frozen=True)
class Check:
    name: str            # default exception_type
    category: str        # integrity | validity | temporal | reconciliation | lifecycle | duplicate | leakage
    disposition: str     # QUARANTINE | FLAG
    description: str
    fn: Callable[[Tables], Iterator["Hit"]]


@dataclass
class Hit:
    table: str
    rows: pd.DataFrame          # offending rows (subset of tables[table])
    detail: pd.Series | str
    exception_type: str | None = None    # overrides Check.name (e.g. FK to theme -> THEME_OUTSIDE_TAXONOMY)
    category: str | None = None          # overrides Check.category
    disposition: str | None = None       # overrides Check.disposition


CHECKS: list[Check] = []


def check(name, category, disposition, description):
    def deco(fn):
        CHECKS.append(Check(name, category, disposition, description, fn))
        return fn
    return deco


def _fields(t):
    return C.ENTITIES[t]["fields"]


# ------------------------------------------------------------------ validity (per field, from the contract)
@check("REQUIRED_MISSING", "validity", "QUARANTINE", "required field is empty")
def required(T):
    for t, df in T.items():
        for x in _fields(t):
            if x["required"]:
                bad = df[df[x["name"]] == ""]
                yield Hit(t, bad, f"{x['name']} is required")


_TYPE_OK = {
    "int": lambda s: s.str.fullmatch(r"-?\d+"),
    "float": lambda s: pd.to_numeric(s, errors="coerce").notna(),
    "date": lambda s: pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").notna(),
    "datetime": lambda s: pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce").notna(),
}


@check("TYPE_INVALID", "validity", "QUARANTINE", "value does not parse as the contract type (int/float/date/datetime)")
def types(T):
    for t, df in T.items():
        for x in _fields(t):
            ok = _TYPE_OK.get(x["type"])
            if ok:
                s = df[x["name"]]
                bad = df[(s != "") & ~ok(s).fillna(False).astype(bool)]
                yield Hit(t, bad, x["name"] + "='" + bad[x["name"]] + f"' is not a {x['type']}")


@check("ENUM_INVALID", "validity", "QUARANTINE", "value not in the contract's allowed list")
def enums(T):
    for t, df in T.items():
        for x in _fields(t):
            if x["allowed"]:
                allowed = {str(a) for a in x["allowed"]} | ({""} if not x["required"] else set())
                bad = df[~df[x["name"]].isin(allowed)]
                yield Hit(t, bad, x["name"] + "='" + bad[x["name"]] + "' not allowed")


def _pattern(x):
    if x["name"] in C.ID_PATTERNS:
        return C.ID_PATTERNS[x["name"]]
    if x["fk"]:
        return C.ID_PATTERNS.get(x["fk"].split(".")[1])
    return None


@check("ID_FORMAT", "validity", "QUARANTINE", "ID does not match its zero-padded pattern")
def id_format(T):
    for t, df in T.items():
        for x in _fields(t):
            pat = _pattern(x) if x["type"] == "id" else None
            if pat:
                s = df[x["name"]]
                bad = df[(s != "") & ~s.str.match(pat)]
                yield Hit(t, bad, x["name"] + "='" + bad[x["name"]] + f"' !~ {pat}")


@check("TAG_UNKNOWN", "validity", "FLAG", "tags contains a value outside the source-tag vocabulary")
def tags(T):
    for t in ("review", "survey_response"):
        df = T[t]
        tok = df["tags"].str.split(";").explode()
        tok = tok[(tok != "") & ~tok.isin(C.SOURCE_TAGS)]
        label_like = tok.str.contains(r"label|sentiment|gold", case=False)
        for mask, et in ((~label_like, None), (label_like, "TEST_LABEL_IN_MODEL_INPUT")):
            hits = tok[mask]
            rows = df.loc[hits.index.unique()]
            detail = hits.groupby(level=0).agg(";".join).reindex(rows.index)
            if et is None:
                yield Hit(t, rows, "unknown tag '" + detail + "'")
            else:
                yield Hit(t, rows, "label-like tag '" + detail + "' in model input", et, "leakage", "QUARANTINE")


# ------------------------------------------------------------------ integrity
@check("PK_DUPLICATE", "integrity", "QUARANTINE", "primary key repeats (first occurrence kept)")
def pk_dup(T):
    for t, df in T.items():
        pk = C.ENTITIES[t]["pk"]
        yield Hit(t, df[df.duplicated(pk, keep="first")], "duplicate primary key")


@check("UNIQUE_VIOLATION", "integrity", "FLAG", "a unique non-key field repeats")
def unique(T):
    for t, df in T.items():
        for x in _fields(t):
            if x["unique"] and C.ENTITIES[t]["pk"] != [x["name"]]:
                bad = df[(df[x["name"]] != "") & df.duplicated(x["name"], keep="first")]
                yield Hit(t, bad, x["name"] + "='" + bad[x["name"]] + "' already used")


@check("FK_MISSING", "integrity", "QUARANTINE", "foreign key (incl. polymorphic source_id) has no parent row")
def fk(T):
    for t, df in T.items():
        for x in _fields(t):
            if x["fk"]:
                pt, pc = x["fk"].split(".")
                s = df[x["name"]]
                bad = df[(s != "") & ~s.isin(T[pt][pc])]
                et = "THEME_OUTSIDE_TAXONOMY" if pt == "theme" else None
                yield Hit(t, bad, x["name"] + "='" + bad[x["name"]] + f"' not found in {pt}", et)
        if {"source_type", "source_id"} <= set(df.columns) and t in ("sentiment_label", "feedback_theme"):
            ok = pd.Series(False, index=df.index)
            for st, (pk, _) in FEEDBACK_TS.items():
                ok |= (df["source_type"] == st) & df["source_id"].isin(T[st][pk])
            bad = df[~ok]
            yield Hit(t, bad, "source " + bad["source_type"] + "/" + bad["source_id"] + " not found")


# ------------------------------------------------------------------ temporal
def _parent(T, child, key, parent, col):
    return T[child][key].map(T[parent].drop_duplicates(key).set_index(key)[col])


@check("DATE_ORDER", "temporal", "FLAG", "dates out of order or outside the feedback window")
def dates(T):
    s = T["survey"]
    yield Hit("survey", s[s["closes_at"] < s["opens_at"]], "closes_at < opens_at")
    th = T["theme"]
    yield Hit("theme", th[(th["effective_to"] != "") & (th["effective_to"] <= th["effective_from"])],
              "effective_to <= effective_from")
    lo, hi = WINDOW_START.isoformat(), WINDOW_END.isoformat()
    ref = REFERENCE_DATE.isoformat()
    for t, ts, end in (("review", "posted_at", hi), ("survey_response", "submitted_at", hi),
                       ("support_ticket", "opened_at", hi), ("support_message", "sent_at", ref),
                       ("ticket_status_event", "event_at", ref)):
        df = T[t]
        d = df[ts].str.slice(0, 10)
        bad = (d < lo) | (d > end) if end == hi else (d < lo) | (d >= ref)   # threads may run past the window, never past 'today'
        yield Hit(t, df[bad], ts + "=" + df[ts] + f" outside {lo}..{end}")
    r = T["survey_response"]
    d = r["submitted_at"].str.slice(0, 10)
    o, c = _parent(T, "survey_response", "survey_id", "survey", "opens_at"), \
        _parent(T, "survey_response", "survey_id", "survey", "closes_at")
    yield Hit("survey_response", r[(d < o) | (d > c)], "submitted outside survey window " + o + ".." + c)
    for t in ("review", "survey_response", "support_ticket"):
        df = T[t]
        created = _parent(T, t, "customer_id", "customer", "created_at")
        ts = {"review": "posted_at", "survey_response": "submitted_at", "support_ticket": "opened_at"}[t]
        yield Hit(t, df[df[ts].str.slice(0, 10) < created], "before customer.created_at=" + created)
    m = T["support_message"]
    opened = _parent(T, "support_message", "ticket_id", "support_ticket", "opened_at")
    closed = _parent(T, "support_message", "ticket_id", "support_ticket", "closed_at").fillna("")
    yield Hit("support_message", m[m["sent_at"] < opened], "sent before ticket opened_at=" + opened)
    yield Hit("support_message", m[(closed != "") & (m["sent_at"] > closed)], "sent after ticket closed_at=" + closed)
    ms = m.sort_values("message_id")
    prev = ms.groupby("ticket_id")["sent_at"].shift()
    yield Hit("support_message", ms[prev.notna() & (ms["sent_at"] < prev)], "sent_at earlier than previous message")
    e = T["ticket_status_event"]
    opened = _parent(T, "ticket_status_event", "ticket_id", "support_ticket", "opened_at")
    yield Hit("ticket_status_event", e[e["event_at"] < opened], "event before ticket opened_at")
    for t, col in (("sentiment_label", "labeled_at"), ("feedback_theme", "tagged_at")):
        df = T[t]
        src = pd.Series("", index=df.index)
        for st, (pk, ts) in FEEDBACK_TS.items():
            mask = df["source_type"] == st
            src[mask] = df.loc[mask, "source_id"].map(T[st].drop_duplicates(pk).set_index(pk)[ts]).fillna("")
        yield Hit(t, df[(src != "") & (df[col] < src)], col + " before the feedback timestamp " + src)


# ------------------------------------------------------------------ reconciliation (derived values recomputed)
@check("DERIVED_MISMATCH", "reconciliation", "FLAG", "a derived value does not equal its recomputation")
def derived(T):
    ref = REFERENCE_DATE.isoformat()
    s = T["survey"]
    want = pd.Series("OPEN", index=s.index).mask(s["opens_at"] > ref, "DRAFT").mask(s["closes_at"] < ref, "CLOSED")
    yield Hit("survey", s[s["status"] != want], "status=" + s["status"] + " but dates give " + want)
    tk, ev = T["support_ticket"], T["ticket_status_event"].sort_values(["ticket_id", "event_at", "event_id"])
    last = tk["ticket_id"].map(ev.groupby("ticket_id")["to_status"].last()).fillna("<no events>")
    yield Hit("support_ticket", tk[tk["current_status"] != last], "current_status=" + tk["current_status"] +
              " but latest event says " + last)
    closed = tk["ticket_id"].map(ev[ev["to_status"] == "CLOSED"].groupby("ticket_id")["event_at"].last()).fillna("")
    yield Hit("support_ticket", tk[tk["closed_at"] != closed], "closed_at='" + tk["closed_at"] +
              "' but CLOSED event at '" + closed + "'")
    # child ids embed the parent id; counters are 1..n per parent
    for t, pk, parent, prefix in (("survey_response", "response_id", "survey_id", "RESP-"),
                                  ("support_message", "message_id", "ticket_id", "MSG-")):
        df = T[t]
        emb = df[pk].str.slice(len(prefix), len(prefix) + 15)
        yield Hit(t, df[emb != df[parent]], pk + " does not embed " + parent + "=" + df[parent])
        n = pd.to_numeric(df[pk].str.slice(-3), errors="coerce")
        size = df.groupby(parent)[pk].transform("size")
        yield Hit(t, df[n > size], "counter exceeds row count of parent (gap in 001..n)")
    r = T["survey_response"]
    sp = _parent(T, "survey_response", "survey_id", "survey", "product_id").fillna("")
    yield Hit("survey_response", r[(sp != "") & (r["product_id"] != sp)], "product_id differs from survey.product_id=" + sp)
    for t, ct in CHANNEL_TYPE_OF.items():
        df = T[t]
        got = _parent(T, t, "channel_id", "channel", "channel_type")
        yield Hit(t, df[got.notna() & (got != ct)], "channel_type=" + got.fillna("") + f", expected {ct}")
    for t in ("review", "survey_response"):
        df = T[t]
        pref = _parent(T, t, "customer_id", "customer", "preferred_language")
        yield Hit(t, df[pref.notna() & (df["language"] != pref)], "language differs from customer preference " + pref.fillna(""))


# ------------------------------------------------------------------ lifecycle
@check("LIFECYCLE_ILLEGAL", "lifecycle", "FLAG", "status transition not allowed by the contract lifecycle")
def lifecycle(T):
    e = T["ticket_status_event"].sort_values(["ticket_id", "event_at", "event_id"])
    legal = C.TRANSITIONS["ticket_status_event"]
    pair = [(f or None, t) for f, t in zip(e["from_status"], e["to_status"])]
    bad = e[[p not in legal for p in pair]]
    yield Hit("ticket_status_event", bad, "illegal transition " + bad["from_status"].mask(bad["from_status"] == "", "None")
              + "->" + bad["to_status"])
    prev = e.groupby("ticket_id")["to_status"].shift().fillna("")
    broken = e[e["from_status"] != prev]
    yield Hit("ticket_status_event", broken, "from_status=" + broken["from_status"] + " but previous to_status=" + prev[broken.index])
    r = T["survey_response"]
    st = _parent(T, "survey_response", "survey_id", "survey", "status")
    yield Hit("survey_response", r[st == "DRAFT"], "response to a DRAFT survey")


# ------------------------------------------------------------------ duplicates
@check("DUPLICATE_RESPONSE", "duplicate", "QUARANTINE", "same customer answered the same survey again (first kept)")
def dup_response(T):
    r = T["survey_response"].sort_values(["submitted_at", "response_id"])
    dup = r[r.duplicated(["customer_id", "survey_id"], keep="first")]
    first = r.drop_duplicates(["customer_id", "survey_id"]).set_index(["customer_id", "survey_id"])
    key = pd.MultiIndex.from_frame(dup[["customer_id", "survey_id"]])
    orig = first.loc[key]
    same = (orig["text"].to_numpy() == dup["text"].to_numpy())
    detail = pd.Series([f"duplicate of {o} ({'same' if s else 'different'} text)"
                        for o, s in zip(orig["response_id"], same)], index=dup.index, dtype=str)
    yield Hit("survey_response", dup, detail)


@check("DUPLICATE_REVIEW", "duplicate", "FLAG", "same customer posted the same text for the same product")
def dup_review(T):
    r = T["review"].sort_values(["posted_at", "review_id"])
    yield Hit("review", r[r.duplicated(["customer_id", "product_id", "text"], keep="first")], "repeated review text")


# ------------------------------------------------------------------ runner
def _feedback_ref(table: str, rows: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(source_type, source_id) of the feedback item a row is about; empty if not feedback-related."""
    if table in FEEDBACK_TS:
        return pd.Series(table, index=rows.index), rows[FEEDBACK_TS[table][0]]
    if table in ("sentiment_label", "feedback_theme"):
        return rows["source_type"], rows["source_id"]
    empty = pd.Series("", index=rows.index)
    return empty, empty


def run_checks(T: Tables) -> pd.DataFrame:
    parts = []
    for chk in CHECKS:
        for h in chk.fn(T):
            if h.rows.empty:
                continue
            st, sid = _feedback_ref(h.table, h.rows)
            pk = C.ENTITIES[h.table]["pk"]
            detail = h.detail if isinstance(h.detail, str) else h.detail.reindex(h.rows.index).astype(str)
            parts.append(pd.DataFrame({
                "table_name": h.table, "record_key": h.rows[pk].astype(str).agg("|".join, axis=1),
                "source_type": st.values, "source_id": sid.values,
                "exception_type": h.exception_type or chk.name, "check_name": chk.name,
                "check_category": h.category or chk.category, "disposition": h.disposition or chk.disposition, "detail": detail}))
    cols = ["table_name", "record_key", "source_type", "source_id", "exception_type", "check_name",
            "check_category", "disposition", "detail"]
    if not parts:
        return pd.DataFrame(columns=cols)
    out = pd.concat(parts, ignore_index=True)[cols]
    return out.drop_duplicates(["table_name", "record_key", "exception_type", "detail"]).sort_values(
        ["table_name", "record_key", "exception_type"], kind="mergesort").reset_index(drop=True)
