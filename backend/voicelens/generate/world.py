"""The simulated world: hidden incidents that CAUSE feedback, with an explicit per-channel lag.

Rule (documented, deterministic given the rng):
  An incident affects one (product, theme). For a feedback item of channel type c on date d it is "active" when
      onset + lag[c] <= d <= end + lag[c]          lag = support 0, review +3, survey +7 days
  While active:  - the product's sampling weight is multiplied by (1 + volume_boost)   (more feedback)
                 - with probability override_prob the item's theme := incident theme and
                   sentiment := negative (worsen) / positive (improve)                    (worse feedback)
  'improve' incidents also have a chronic pre-onset phase (pre_onset_prob of negative on that theme),
  so the improvement is visible as a drop in negative share after onset.
The detector is later scored on whether/when it finds each incident (time-to-detect, per channel).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from .config import CHANNEL_LAG_DAYS, WINDOW_END
from .taxonomy import PRODUCTS

INCIDENTS = [
    {"incident_id": "INC-01", "name": "Carrier network outage",
     "description": "Regional carrier outage delays QuickDrop Express parcels.",
     "product_id": "PROD-0010", "theme_code": "late_delivery", "direction": "worsen",
     "onset_date": date(2026, 7, 20), "end_date": date(2026, 8, 9),
     "volume_boost": 1.0, "override_prob": 0.55, "pre_onset_prob": 0.0},
    {"incident_id": "INC-02", "name": "Billing release charges cards twice",
     "description": "A billing release charges StreamNest Premium subscribers twice.",
     "product_id": "PROD-0004", "theme_code": "double_charge", "direction": "worsen",
     "onset_date": date(2026, 6, 22), "end_date": date(2026, 7, 5),
     "volume_boost": 1.0, "override_prob": 0.55, "pre_onset_prob": 0.0},
    {"incident_id": "INC-03", "name": "Login outage after app update",
     "description": "App update 4.2 breaks verification codes for Lumo Wallet users.",
     "product_id": "PROD-0001", "theme_code": "account_login", "direction": "worsen",
     "onset_date": date(2026, 5, 11), "end_date": date(2026, 5, 24),
     "volume_boost": 1.0, "override_prob": 0.55, "pre_onset_prob": 0.0},
    {"incident_id": "INC-04", "name": "Performance fix release",
     "description": "TrekTrack 6.0 fixes long-standing crashes; negative app_performance feedback falls.",
     "product_id": "PROD-0002", "theme_code": "app_performance", "direction": "improve",
     "onset_date": date(2026, 8, 24), "end_date": WINDOW_END,
     "volume_boost": 0.0, "override_prob": 0.45, "pre_onset_prob": 0.35},
]
_PRODUCT_IDS = [p[0] for p in PRODUCTS]


def signal_window(inc: dict, channel_type: str) -> tuple[date, date]:
    lag = timedelta(days=CHANNEL_LAG_DAYS[channel_type])
    return inc["onset_date"] + lag, inc["end_date"] + lag


def phase(inc: dict, product_id: str, channel_type: str, d: date) -> str | None:
    """'post' while the incident signal is active, 'pre' for the chronic phase of an improve incident."""
    if product_id != inc["product_id"]:
        return None
    start, end = signal_window(inc, channel_type)
    if start <= d <= end:
        return "post"
    if inc["direction"] == "improve" and d < start:
        return "pre"
    return None


def product_weights(channel_type: str, d: date) -> np.ndarray:
    w = np.ones(len(_PRODUCT_IDS))
    for inc in INCIDENTS:
        if inc["volume_boost"] and phase(inc, inc["product_id"], channel_type, d) == "post":
            w[_PRODUCT_IDS.index(inc["product_id"])] *= 1 + inc["volume_boost"]
    return w / w.sum()


def incident_override(rng: np.random.Generator, product_id: str, channel_type: str, d: date):
    """Return (incident_id, theme_code, sentiment, phase) if an incident causes this item, else None."""
    for inc in INCIDENTS:
        ph = phase(inc, product_id, channel_type, d)
        if ph == "post" and rng.random() < inc["override_prob"]:
            return (inc["incident_id"], inc["theme_code"],
                    "negative" if inc["direction"] == "worsen" else "positive", "post")
        if ph == "pre" and rng.random() < inc["pre_onset_prob"]:
            return inc["incident_id"], inc["theme_code"], "negative", "pre"
    return None
