"""Fixed generator parameters. No wall clock: every date derives from REFERENCE_DATE / the window below."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

SEED = 20261022
REFERENCE_DATE = date(2026, 10, 1)      # "today" for the synthetic world (lifecycle cut-off)
WINDOW_START = date(2026, 4, 6)         # Monday, ISO week 2026-W15
WINDOW_END = date(2026, 9, 27)          # Sunday, ISO week 2026-W39  -> 25 full weeks
CUSTOMER_SINCE = date(2024, 1, 1)

# Channel lag (days after incident onset before the signal shows in that channel type).
CHANNEL_LAG_DAYS = {"support": 0, "review": 3, "survey": 7}

BASE = {  # volumes at --scale 1.0 (problem statement: 50k reviews/responses + 20k support messages)
    "customers": 10_000,
    "reviews": 30_000,
    "responses": 20_000,
    "support_messages": 20_000,
    "eval_items": 2_000,
}
MAX_RESPONSES_PER_SURVEY = 400          # keeps the 3-digit RESP counter far below 999
INPUT_TAG_SHARE = 0.30                  # share of train items carrying source-system tags
SENTIMENTS = ("positive", "negative", "neutral", "mixed")


@dataclass(frozen=True)
class Volumes:
    customers: int
    reviews: int
    responses: int
    support_messages: int
    tickets: int
    surveys: int
    eval_items: int
    anomalies_per_type: int


def volumes(scale: float) -> Volumes:
    if scale <= 0:
        raise ValueError("--scale must be > 0")
    n = {k: max(1, round(v * scale)) for k, v in BASE.items()}
    customers = max(n["customers"], 50)
    responses = n["responses"]
    # one response per (customer, survey): each survey needs <= ~half the customer base
    surveys = max(3, math.ceil(responses / MAX_RESPONSES_PER_SURVEY), math.ceil(responses / (0.5 * customers)))
    return Volumes(
        customers=customers,
        reviews=n["reviews"],
        responses=responses,
        support_messages=n["support_messages"],
        # 2-6 messages per ticket (mean ~4); dividing by 3.9 makes the total reliably reach the target (>= 20,000 at 1.0)
        tickets=max(1, round(n["support_messages"] / 3.9)),
        surveys=surveys,
        eval_items=max(40, n["eval_items"]),
        anomalies_per_type=max(3, round(40 * scale)),
    )
