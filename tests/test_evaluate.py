"""Metric functions on hand-made cases."""
import pandas as pd
import pytest

from voicelens.evaluate import metrics as M


def test_classification_accuracy_f1_and_confusion():
    gold = pd.Series(["positive", "negative", "neutral", "mixed", "negative"])
    pred = pd.Series(["positive", "negative", "neutral", "negative", "negative"])
    r = M.classification(gold, pred)
    assert r["accuracy"] == 0.8 and r["per_class"]["mixed"]["recall"] == 0.0
    assert r["per_class"]["negative"]["precision"] == pytest.approx(2 / 3, abs=1e-4)
    assert r["confusion"]["matrix"][3][1] == 1          # gold mixed -> predicted negative


def test_theme_sets_exact_and_micro():
    r = M.theme_sets(pd.Series(["A|B", "C", "D"]), pd.Series(["B|A", "C|E", ""]))
    assert r["exact_match"] == pytest.approx(1 / 3, abs=1e-4)
    assert r["micro_precision"] == 0.75 and r["micro_recall"] == 0.75


def test_coverage_curve_and_tau_choice():
    conf = pd.Series([0.9, 0.8, 0.5, 0.4])
    other = pd.Series([False, False, False, True])
    ok = pd.Series([True, True, False, False])
    curve = M.coverage_curve(conf, other, ok, taus=[0.3, 0.6, 0.85])
    assert curve[0] == {"tau": 0.3, "coverage": 0.75, "auto_accuracy": 0.6667}
    assert curve[1]["auto_accuracy"] == 1.0
    assert M.choose_tau(curve, 0.95)["tau"] == 0.6     # highest coverage that meets the target


def test_incident_matching_parent_child_false_alarms_and_recovery():
    inc = pd.DataFrame([{"incident_id": "INC-01", "product_id": "P1", "theme_id": "T-child", "direction": "worsen",
                         "onset_date": "2026-07-20", "end_date": "2026-08-09",
                         "lag_support_days": 0, "lag_review_days": 3, "lag_survey_days": 7}])
    base = {"lead_channel": "support", "first_support_date": "2026-07-21", "first_review_date": "2026-07-23",
            "first_survey_date": ""}
    alerts = pd.DataFrame([
        {"alert_id": "A1", "product_id": "P1", "theme_id": "T-parent", "direction": "worsen", "kind": "worsen",
         "detected_date": "2026-07-25", **base},                                         # parent theme still counts
        {"alert_id": "A2", "product_id": "P2", "theme_id": "T-x", "direction": "worsen", "kind": "worsen",
         "detected_date": "2026-07-01", **base},                                         # false alarm
        {"alert_id": "A3", "product_id": "P1", "theme_id": "T-child", "direction": "improve", "kind": "recovery",
         "detected_date": "2026-08-20", **base}])                                        # recovery: not a false alarm
    rows, false = M.match_incidents(inc, alerts, {"T-child": "T-parent"})
    assert rows[0]["detected"] and rows[0]["time_to_detect_days"] == 5 and rows[0]["lead_channel_correct"]
    assert rows[0]["review_lag_measured"] == 3 and rows[0]["survey_lag_measured"] is None
    assert [f["alert_id"] for f in false] == ["A2"]
