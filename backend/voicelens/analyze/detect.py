"""Stage 6 - detect: for every product x theme and every day, compare a rolling 7-day window with the 28 days before
it. Day-level resolution makes time-to-detect measurable in days (weekly buckets could only say 'within 7 days').

  WORSEN   excess negatives: exact Poisson tail P(X >= obs | lam), lam = (baseline negatives + 1)/28 x 7;
           fires if p <= P_MAX, obs >= MIN_NEG and negative share rose by >= MIN_SHARE_RISE.
  IMPROVE  negative share fell by >= MIN_SHARE_DROP with z >= Z_IMPROVE (baseline >= 20, window >= 10 items).
~80 series x ~140 days = ~11k tests, so P_MAX = 1e-5 (Bonferroni-style, ~0.1 expected false firings per run).
Consecutive firing days (gaps <= MERGE_GAP) form a run; a run becomes an alert only when it persists PERSIST days,
and detected_date = that confirmation day (no hindsight). An improve alert on a key whose worsen alert ended within
RECOVERY_DAYS is labelled kind=recovery. Each channel is also tested on its own series (lenient z), giving the first
firing date per channel and the lead channel. Thresholds are fixed by the reasoning above - never tuned on incidents.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

WINDOW, BASELINE = 7, 28
P_MAX, MIN_NEG, MIN_SHARE_RISE = 1e-5, 8, 0.15
MIN_SHARE_DROP, Z_IMPROVE, MIN_BASE_N, MIN_WIN_N = 0.30, 4.0, 20, 10
PERSIST, RECOVERY_DAYS = 3, 28
CH_Z_MIN, CH_MIN_NEG = 2.0, 3                      # per-channel test (smaller samples)
MERGE_GAP = 2
CHANNELS = ["support", "review", "survey"]
PARAMS = {k: v for k, v in globals().items() if k.isupper() and k != "CHANNELS"}


def _daily(f: pd.DataFrame, keys: list[str], days: pd.DatetimeIndex) -> pd.DataFrame:
    g = f.groupby(keys + ["date"]).agg(n=("source_id", "size"), neg=("neg", "sum"))
    full = pd.MultiIndex.from_tuples([(*k, d) for k in g.index.droplevel("date").unique() for d in days],
                                     names=keys + ["date"])
    return g.reindex(full, fill_value=0).reset_index()


def poisson_sf(obs: float, lam: float) -> float:
    """P(X >= obs) for X ~ Poisson(lam), exact."""
    if obs <= 0:
        return 1.0
    k = np.arange(int(obs))
    return float(max(0.0, 1.0 - np.exp(-lam + k * math.log(lam) - np.array([math.lgamma(i + 1) for i in k])).sum()))


def poisson_log10_sf(obs: float, lam: float) -> float:
    """log10 P(X >= obs), computed in log space so tiny tails do not underflow to 0."""
    if obs <= 0:
        return 0.0
    ks = np.arange(int(obs), int(obs) + 400)
    lp = -lam + ks * math.log(lam) - np.array([math.lgamma(k + 1) for k in ks])
    m = lp.max()
    return float((m + math.log(np.exp(lp - m).sum())) / math.log(10))


def normal_log10_sf(z: float) -> float:
    """log10 P(Z >= z) for a standard normal; asymptotic form for large z."""
    if z < 30:
        return math.log10(max(0.5 * math.erfc(z / math.sqrt(2)), 1e-300))
    return -(z * z / 2 + math.log(z * math.sqrt(2 * math.pi))) / math.log(10)


def magnitude(direction: str, row) -> float:
    """M = -log10(p): Richter-style strength of the evidence. M >= 5 <=> p <= 1e-5 (the worsen gate)."""
    if direction == "worsen":
        return round(-poisson_log10_sf(row["w_neg"], (row["b_neg"] + 1) / BASELINE * WINDOW), 2)
    return round(-normal_log10_sf(float(row["z_improve"])), 2)


def _signals(d: pd.DataFrame, keys: list[str], z_min: float | None, min_neg: int) -> pd.DataFrame:
    d = d.sort_values(keys + ["date"]).copy()
    grp = d.groupby(keys, sort=False)
    for col in ("n", "neg"):
        d[f"w_{col}"] = grp[col].transform(lambda s: s.rolling(WINDOW, min_periods=WINDOW).sum())
        d[f"b_{col}"] = grp[col].transform(lambda s: s.shift(WINDOW).rolling(BASELINE, min_periods=BASELINE).sum())
    lam = (d["b_neg"] + 1) / BASELINE * WINDOW
    d["z"] = (d["w_neg"] - lam) / np.sqrt(lam)
    d["w_share"] = d["w_neg"] / d["w_n"].where(d["w_n"] > 0)
    d["b_share"] = d["b_neg"] / d["b_n"].where(d["b_n"] > 0)
    d["shift"] = d["w_share"] - d["b_share"]
    base = (d["w_neg"] >= min_neg) & (d["shift"].fillna(1) >= MIN_SHARE_RISE)
    if z_min is None:                               # combined series: exact Poisson tail
        d["p"] = [poisson_sf(o, l) if b else 1.0 for o, l, b in zip(d["w_neg"], lam, base)]
        d["worsen"] = base & (d["p"] <= P_MAX)
    else:                                           # per-channel: lenient z, only used for lead-lag dating
        d["worsen"] = base & (d["z"] >= z_min)
    se = np.sqrt(d["b_share"] * (1 - d["b_share"]) / d["w_n"].clip(lower=1) + 1e-9)
    d["z_improve"] = -d["shift"] / se
    n_min = (MIN_BASE_N, MIN_WIN_N) if z_min is None else (MIN_BASE_N // 2, MIN_WIN_N // 2)
    d["improve"] = (d["b_n"] >= n_min[0]) & (d["w_n"] >= n_min[1]) & (d["shift"] <= -MIN_SHARE_DROP) & \
        (d["z_improve"] >= (Z_IMPROVE if z_min is None else 2.0))
    return d.dropna(subset=["b_n"])


def _runs(dates: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    out, start, prev = [], None, None
    for d in sorted(dates):
        if start is None:
            start = prev = d
        elif (d - prev).days <= MERGE_GAP + 1:
            prev = d
        else:
            out.append((start, prev))
            start = prev = d
    return out + ([(start, prev)] if start is not None else [])


def detect(f: pd.DataFrame, run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """f = aggregate.facts(). -> (alerts, alert_evidence)."""
    days = pd.date_range(f["date"].min(), f["date"].max(), freq="D")
    last_day = days[-1]
    combined = _signals(_daily(f, ["product_id", "theme_id"], days), ["product_id", "theme_id"], None, MIN_NEG)
    per_ch = _signals(_daily(f, ["product_id", "theme_id", "channel_type"], days),
                      ["product_id", "theme_id", "channel_type"], CH_Z_MIN, CH_MIN_NEG)
    alerts, evidence = [], []
    for direction, flag, zcol in (("worsen", "worsen", "z"), ("improve", "improve", "z_improve")):
        for (pid, tid), g in combined[combined[flag]].groupby(["product_id", "theme_id"]):
            for start, end in _runs(g["date"]):
                span = g[(g["date"] >= start) & (g["date"] <= end)]
                if len(span) < PERSIST:
                    continue
                detected = span["date"].iloc[PERSIST - 1]
                peak = span.loc[span[zcol].idxmax()]
                a = {"product_id": pid, "theme_id": tid, "direction": direction, "kind": direction,
                     "start_date": start, "detected_date": detected,
                     "peak_date": peak["date"], "end_date": end,
                     "status": "ACTIVE" if (last_day - end).days < 3 else "ENDED",
                     "peak_z": round(float(peak[zcol]), 3), "magnitude": magnitude(direction, peak), "baseline_share": round(float(peak["b_share"]), 4),
                     "window_share": round(float(peak["w_share"]), 4), "shift": round(float(peak["shift"]), 4),
                     "window_items": int(peak["w_n"])}
                ch = per_ch[(per_ch["product_id"] == pid) & (per_ch["theme_id"] == tid) & per_ch[flag]
                            & (per_ch["date"] >= start - pd.Timedelta(days=WINDOW)) & (per_ch["date"] <= end)]
                first = ch.groupby("channel_type")["date"].min()
                for c in CHANNELS:
                    a[f"first_{c}_date"] = first.get(c)
                a["lead_channel"] = min(first.index, key=lambda c: (first[c], CHANNELS.index(c))) if len(first) else None
                alerts.append(a)
                for role, day in (("trigger", start), ("peak", peak["date"])):
                    w = f[(f["product_id"] == pid) & (f["theme_id"] == tid) & (f["date"] > day - pd.Timedelta(days=WINDOW))
                          & (f["date"] <= day)]
                    if direction == "worsen":
                        w = w[w["neg"] == 1]
                    evidence.append(w[["source_type", "source_id"]].assign(_k=len(alerts) - 1, role=role))
    if not alerts:
        return pd.DataFrame(), pd.DataFrame(columns=["alert_id", "source_type", "source_id", "role"])
    al = pd.DataFrame(alerts).sort_values(["start_date", "product_id", "theme_id", "direction"], kind="mergesort")
    for i, a in al[al["direction"] == "improve"].iterrows():
        prior = al[(al["direction"] == "worsen") & (al["product_id"] == a["product_id"]) & (al["theme_id"] == a["theme_id"])
                   & (al["end_date"] <= a["start_date"]) & (al["end_date"] >= a["start_date"] - pd.Timedelta(days=RECOVERY_DAYS))]
        if len(prior):
            al.at[i, "kind"] = "recovery"
    al["alert_id"] = [f"ALR-{i:06d}" for i in range(1, len(al) + 1)]
    ev = pd.concat(evidence).merge(al[["alert_id"]].reset_index(names="_k"), on="_k")
    ev = ev.sort_values("role", ascending=False).drop_duplicates(["alert_id", "source_type", "source_id"])  # trigger wins
    al["evidence_count"] = al["alert_id"].map(ev.groupby("alert_id").size()).fillna(0).astype(int)
    al["run_id"] = run_id
    for c in ("start_date", "detected_date", "peak_date", "end_date") + tuple(f"first_{c}_date" for c in CHANNELS):
        al[c] = pd.to_datetime(al[c]).dt.strftime("%Y-%m-%d")
    return al.reset_index(drop=True), ev[["alert_id", "source_type", "source_id", "role"]].reset_index(drop=True)
