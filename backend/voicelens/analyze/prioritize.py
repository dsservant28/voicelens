"""Stage 7 - prioritize: priority = volume x neg_share x severity_weight x (1 + shift). Inputs are stored with the score.
Candidates: worsen alerts (window = start-6 .. end) and chronic issues (last 28 days, high negative share, no alert)."""
from __future__ import annotations

import pandas as pd

CHRONIC_DAYS, CHRONIC_MIN_N, CHRONIC_MIN_SHARE = 28, 15, 0.6


def score(volume: int, neg_share: float, severity: int, shift: float) -> float:
    return round(volume * neg_share * severity * (1 + max(shift, 0.0)), 2)


def _inputs(w: pd.DataFrame, severity: int, shift: float) -> dict:
    items = w.drop_duplicates(["source_type", "source_id"])
    vol, share = len(items), float(items["neg"].mean()) if len(items) else 0.0
    return {"volume": vol, "neg_share": round(share, 4), "severity_weight": int(severity), "shift": round(shift, 4),
            "priority": score(vol, share, severity, shift)}


def candidates(f: pd.DataFrame, alerts: pd.DataFrame, evidence: pd.DataFrame, severity: dict[str, int]) -> list[dict]:
    out = []
    worsen = alerts[alerts["direction"] == "worsen"] if len(alerts) else alerts
    for a in worsen.itertuples():
        lo, hi = pd.Timestamp(a.start_date) - pd.Timedelta(days=6), pd.Timestamp(a.end_date)
        w = f[(f["product_id"] == a.product_id) & (f["theme_id"] == a.theme_id) & f["date"].between(lo, hi)]
        ids = evidence.loc[evidence["alert_id"] == a.alert_id, "source_id"].tolist()
        out.append({"kind": "alert", "product_id": a.product_id, "theme_id": a.theme_id, "alert_id": a.alert_id,
                    "duration_days": (hi - pd.Timestamp(a.start_date)).days + 1, "evidence": ids,
                    **_inputs(w, severity[a.theme_id], a.shift)})
    last = f["date"].max()
    recent = f[f["date"] > last - pd.Timedelta(days=CHRONIC_DAYS)]
    alerted = set(zip(worsen["product_id"], worsen["theme_id"])) if len(worsen) else set()
    for (pid, tid), w in recent.groupby(["product_id", "theme_id"]):
        inp = _inputs(w, severity[tid], 0.0)
        if (pid, tid) in alerted or inp["volume"] < CHRONIC_MIN_N or inp["neg_share"] < CHRONIC_MIN_SHARE:
            continue
        out.append({"kind": "chronic", "product_id": pid, "theme_id": tid, "alert_id": None,
                    "duration_days": CHRONIC_DAYS, "evidence": w.loc[w["neg"] == 1, "source_id"].unique().tolist(), **inp})
    return sorted(out, key=lambda c: -c["priority"])
