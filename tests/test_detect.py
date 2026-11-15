"""Stages 5-8 on synthetic series: a planted step change is detected on time with the right lead channel, a flat
series stays silent, the Poisson tail is exact, priority follows the formula, action upserts never duplicate."""
import math

import pandas as pd
import pytest

from voicelens.analyze import actions as A
from voicelens.analyze.aggregate import weekly
from voicelens.analyze.detect import detect, poisson_sf
from voicelens.analyze.prioritize import candidates, score

DAYS = pd.date_range("2026-04-06", "2026-07-31", freq="D")
ONSET = pd.Timestamp("2026-06-15")


def _facts(step: bool) -> pd.DataFrame:
    rows, n = [], 0
    for i, d in enumerate(DAYS):
        plan = [("support", int(i % 3 == 0)), ("review", int(i % 3 == 1)), ("survey", int(i % 3 == 2)),
                ("review", 0)]                                                 # 4 items/day, 1 negative (rotating)
        if step and d >= ONSET:
            plan += [("support", 1)] * 4                                       # support moves on day 0
        if step and d >= ONSET + pd.Timedelta(days=3):
            plan += [("review", 1)] * 2                                        # reviews follow 3 days later
        for ch, neg in plan:
            n += 1
            rows.append({"source_type": "review", "source_id": f"X{n}", "product_id": "PROD-0001",
                         "theme_id": "THEME-000011", "channel_type": ch, "date": d,
                         "week_start": (d - pd.Timedelta(days=d.weekday())).date(), "neg": neg, "score_norm": None})
    return pd.DataFrame(rows)


def test_step_change_detected_quickly_with_support_leading():
    al, ev = detect(_facts(True), "RUN-000001")
    w = al[al["direction"] == "worsen"]
    assert len(w) == 1
    a = w.iloc[0]
    assert 0 <= (pd.Timestamp(a["detected_date"]) - ONSET).days <= 5
    assert a["lead_channel"] == "support" and a["first_support_date"] <= a["first_review_date"]
    assert a["evidence_count"] > 0 and set(ev["alert_id"]) == {a["alert_id"]}


def test_flat_series_raises_no_alert():
    al, _ = detect(_facts(False), "RUN-000001")
    assert len(al) == 0


def test_poisson_tail_is_exact():
    lam = 2.0
    exact = 1 - sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(5))
    assert poisson_sf(5, lam) == pytest.approx(exact) and poisson_sf(0, lam) == 1.0


def test_weekly_cells_reconcile_with_members():
    f = _facts(True)
    cells, members = weekly(f, "RUN-000001")
    assert cells["n_items"].sum() == len(members) == len(f)
    assert (cells["neg_share"] == (cells["n_negative"] / cells["n_items"]).round(4)).all()


def test_priority_formula_and_action_upsert():
    assert score(100, 0.5, 3, 0.4) == 210.0 and score(10, 1.0, 1, -0.5) == 10.0      # negative shift ignored
    f = _facts(True)
    al, ev = detect(f, "RUN-000001")
    cands = candidates(f, al, ev, {"THEME-000011": 3})
    assert cands[0]["kind"] == "alert" and cands[0]["priority"] >= A.P_MIN
    args = ({"THEME-000011": "late_delivery"}, {"PROD-0001": "Lumo Wallet"}, "2026-08-01 00:00:00", 1, 1)
    new, upd, evt = A.plan(cands, pd.DataFrame(), *args)
    assert len(new) == 1 and len(upd) == 0 and evt.iloc[0]["to_status"] == "OPEN"
    assert new.iloc[0]["owner_role"] == "logistics_ops" and "Lumo Wallet" in new.iloc[0]["recommendation"]
    new2, upd2, evt2 = A.plan(cands, new[["action_item_id", "product_id", "theme_id", "kind"]], *args)
    assert len(new2) == 0 and len(upd2) == 1 and len(evt2) == 0                         # rerun refreshes, no duplicate
