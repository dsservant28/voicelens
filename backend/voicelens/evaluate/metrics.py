"""Pure metric functions (no I/O). evaluate/ is the ONLY package allowed to read ground truth (policy R1)."""
from __future__ import annotations

import numpy as np
import pandas as pd

SENT = ["positive", "negative", "neutral", "mixed"]


def classification(gold: pd.Series, pred: pd.Series, labels=SENT) -> dict:
    gold, pred = gold.reset_index(drop=True), pred.reset_index(drop=True)
    per = {}
    for c in labels:
        tp = int(((pred == c) & (gold == c)).sum())
        p = tp / max(int((pred == c).sum()), 1)
        r = tp / max(int((gold == c).sum()), 1)
        per[c] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
                  "support": int((gold == c).sum())}
    cm = pd.crosstab(gold, pred).reindex(index=labels, columns=labels, fill_value=0)
    return {"n": len(gold), "accuracy": round(float((gold == pred).mean()), 4) if len(gold) else None,
            "macro_f1": round(float(np.mean([per[c]["f1"] for c in labels])), 4), "per_class": per,
            "confusion": {"labels": labels, "matrix": cm.values.tolist()}}


def theme_sets(gold: pd.Series, pred: pd.Series) -> dict:
    g = [set(x.split("|")) - {""} for x in gold.fillna("")]
    p = [set(x.split("|")) - {""} for x in pred.fillna("")]
    tp = sum(len(a & b) for a, b in zip(g, p))
    prec, rec = tp / max(sum(map(len, p)), 1), tp / max(sum(map(len, g)), 1)
    return {"n": len(g), "exact_match": round(float(np.mean([a == b for a, b in zip(g, p)])), 4),
            "micro_precision": round(prec, 4), "micro_recall": round(rec, 4),
            "micro_f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0}


def slices(df: pd.DataFrame, by: str) -> list[dict]:
    """df has columns ok (bool), theme_ok (bool), auto (bool), plus the slice column."""
    out = []
    for k, g in df.groupby(by):
        out.append({by: k, "n": len(g), "accuracy": round(float(g["ok"].mean()), 4),
                    "theme_exact": round(float(g["theme_ok"].mean()), 4),
                    "coverage": round(float(g["auto"].mean()), 4),
                    "auto_accuracy": round(float(g.loc[g["auto"], "ok"].mean()), 4) if g["auto"].any() else None})
    return out


def coverage_curve(conf: pd.Series, other_reasons: pd.Series, ok: pd.Series, taus=None) -> list[dict]:
    """Auto = confidence >= tau and no non-confidence review reason. Accuracy measured on auto items."""
    taus = taus if taus is not None else [round(t, 2) for t in np.arange(0.30, 0.951, 0.05)]
    out = []
    for t in taus:
        auto = (conf >= t) & ~other_reasons
        out.append({"tau": t, "coverage": round(float(auto.mean()), 4),
                    "auto_accuracy": round(float(ok[auto].mean()), 4) if auto.any() else None})
    return out


def choose_tau(curve: list[dict], target: float) -> dict:
    ok = [c for c in curve if c["auto_accuracy"] is not None and c["auto_accuracy"] >= target]
    if ok:
        return max(ok, key=lambda c: (c["coverage"], -c["tau"]))
    return max((c for c in curve if c["auto_accuracy"] is not None), key=lambda c: c["auto_accuracy"])


def review_sample(eval_items: pd.DataFrame, per_class: int = 25, seed: int = 20261022) -> pd.DataFrame:
    """Blind human-review sample: up to per_class eval items per gold sentiment, shuffled into one review order.
    eval_items: source_type, source_id, sentiment (gold). Returns source_type, source_id, sample_rank (NO label)."""
    rng = np.random.default_rng(seed)
    parts = []
    for _, g in eval_items.sort_values(["source_type", "source_id"]).groupby("sentiment"):
        parts.append(g.iloc[rng.permutation(len(g))[:per_class]])
    s = pd.concat(parts)[["source_type", "source_id"]]
    s = s.iloc[rng.permutation(len(s))].reset_index(drop=True)
    s["sample_rank"] = s.index + 1
    return s


def match_incidents(inc: pd.DataFrame, alerts: pd.DataFrame, parent: dict, grace_days: int = 14) -> tuple[list, list]:
    """An alert detects an incident if product, theme (or parent/child) and direction match and
    detected_date is within [onset, end + grace]. -> (per-incident rows, unmatched non-recovery alerts)."""
    used, rows = set(), []
    for i in inc.itertuples():
        def related(t):
            return t == i.theme_id or parent.get(t) == i.theme_id or parent.get(i.theme_id) == t
        onset, end = pd.Timestamp(i.onset_date), pd.Timestamp(i.end_date) + pd.Timedelta(days=grace_days)
        cand = alerts[(alerts["product_id"] == i.product_id) & alerts["theme_id"].map(related)
                      & (alerts["direction"] == i.direction)
                      & pd.to_datetime(alerts["detected_date"]).between(onset, end)] if len(alerts) else alerts
        row = {"incident_id": i.incident_id, "product_id": i.product_id, "theme_id": i.theme_id,
               "direction": i.direction, "onset_date": i.onset_date, "detected": bool(len(cand))}
        if len(cand):
            a = cand.sort_values("detected_date").iloc[0]
            used.update(cand["alert_id"])
            row.update({"alert_id": a["alert_id"], "detected_date": a["detected_date"],
                        "time_to_detect_days": (pd.Timestamp(a["detected_date"]) - onset).days,
                        "lead_channel": a["lead_channel"],
                        "lead_channel_correct": a["lead_channel"] == min(
                            ("support", "review", "survey"), key=lambda c: getattr(i, f"lag_{c}_days"))})
            for c in ("support", "review", "survey"):
                first = a.get(f"first_{c}_date")
                row[f"{c}_lag_measured"] = (pd.Timestamp(first) - onset).days if isinstance(first, str) and first else None
                row[f"{c}_lag_designed"] = int(getattr(i, f"lag_{c}_days"))
        rows.append(row)
    false = [] if not len(alerts) else alerts[~alerts["alert_id"].isin(used) & (alerts["kind"] != "recovery")][
        ["alert_id", "product_id", "theme_id", "kind", "detected_date"]].to_dict("records")
    return rows, false
