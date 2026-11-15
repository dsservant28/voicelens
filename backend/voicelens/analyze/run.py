"""Stages 2-4 orchestration: normalize -> sentiment + themes -> label check -> abstain -> write (idempotent).
Writes app.pipeline_run, app.feedback_item, app.prediction and analysis rows of app.data_exception (PII_LEAK,
LABEL_CONTRADICTS_TEXT). The output is validated against the same contract as the input before it is written."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

from ..db.load import copy_df
from ..db.models import TABLES, metadata
from ..generate.contract import columns
from ..validate.checks import run_checks
from . import route as R
from .normalize import build_feedback
from .sentiment import classify
from .themes import ThemeClassifier
from . import actions as A, detect as D, prioritize as P
from .insights import run_insights

HERE = Path(__file__).resolve().parent
RULE_FILES = ("lexicon.py", "sentiment.py", "themes.py", "normalize.py", "route.py", "aggregate.py", "detect.py",
              "prioritize.py", "actions.py")
FMT = "%Y-%m-%d %H:%M:%S"


def rules_hash() -> str:
    h = hashlib.sha256()
    for f in RULE_FILES:
        h.update((HERE / f).read_bytes())
    return h.hexdigest()[:12]


def _source_labels(engine: Engine) -> pd.DataFrame:
    sql = "SELECT source_type, source_id, sentiment AS input_label FROM raw.sentiment_label WHERE labeler = 'source_system'"
    with engine.connect() as c:
        return pd.read_sql(sql, c).drop_duplicates(["source_type", "source_id"])


def analyze(engine: Engine, tau: float = R.TAU) -> dict:
    started = datetime.now()
    with engine.begin() as c:
        metadata.create_all(c, tables=[TABLES[t] for t in ("pipeline_run", "feedback_item", "prediction")],
                            checkfirst=True)
        run_no = c.execute(text("SELECT count(*) FROM app.pipeline_run")).scalar_one() + 1
        exc_no = c.execute(text("SELECT coalesce(max(substr(exception_id, 5)::int), 0) FROM app.data_exception "
                                "WHERE detected_by = 'validation'")).scalar_one()
    run_id = f"RUN-{run_no:06d}"
    fb, pii = build_feedback(engine)
    themes = ThemeClassifier(pd.read_sql("SELECT * FROM raw.theme", engine),
                             pd.read_sql("SELECT name FROM raw.product", engine)["name"].tolist())
    labels = _source_labels(engine)
    fb = fb.merge(labels, on=["source_type", "source_id"], how="left")

    preds, conflicts = [], []
    for r in fb.itertuples(index=False):
        p = classify(r.redacted_text, r.language_detected, bool(r.code_mixed), r.language_detected != r.language)
        theme_ids, t_ev = themes.classify(r.redacted_text)
        conflict = (isinstance(r.input_label, str) and {r.input_label, p["sentiment"]} == {"positive", "negative"}
                    and p["confidence"] >= R.LABEL_CONFLICT_MIN_CONF)
        if conflict:
            conflicts.append({"source_type": r.source_type, "source_id": r.source_id,
                              "detail": f"input label={r.input_label} but text predicts {p['sentiment']} "
                                        f"(conf {p['confidence']}, evidence {' '.join(p['evidence'])})"})
        rt, why = R.route(p, len(theme_ids), r.score_norm, conflict, tau)
        preds.append({"source_type": r.source_type, "source_id": r.source_id, "sentiment": p["sentiment"],
                      "confidence": p["confidence"], "pos_score": p["pos"], "neg_score": p["neg"], "theme_ids": "|".join(theme_ids),
                      "evidence": "|".join(p["evidence"] + t_ev), "rules_fired": "|".join(p["rules"]) or "NONE",
                      "route": rt, "route_reason": why, "run_id": run_id})
    pred = pd.DataFrame(preds)

    now = datetime.now().strftime(FMT)
    exc = pd.concat([
        pii.assign(exception_type="PII_LEAK", check_name="normalize.redact", check_category="privacy"),
        pd.DataFrame(conflicts, columns=["source_type", "source_id", "detail"]).assign(
            exception_type="LABEL_CONTRADICTS_TEXT", check_name="label_check", check_category="label_quality"),
    ], ignore_index=True)
    exc.insert(0, "exception_id", [f"EXC-{exc_no + i:06d}" for i in range(1, len(exc) + 1)])
    exc["table_name"], exc["record_key"] = exc["source_type"], exc["source_id"]
    exc["disposition"], exc["detected_by"], exc["detected_at"], exc["resolution_status"] = "FLAG", "analysis", now, "OPEN"

    items = fb.assign(event_at=fb["event_at"].dt.strftime(FMT), week_start=fb["week_start"].astype(str),
                      run_id=run_id)[columns("feedback_item")]
    params = {"tau": tau, "rating_conflict": [R.RATING_LOW, R.RATING_HIGH],
              "label_conflict_min_conf": R.LABEL_CONFLICT_MIN_CONF, "max_themes": 2,
              "detect": D.PARAMS, "chronic": [P.CHRONIC_DAYS, P.CHRONIC_MIN_N, P.CHRONIC_MIN_SHARE],
              "actions": {"p_min": A.P_MIN, "min_alert_days": A.MIN_ALERT_DAYS}}
    run = pd.DataFrame([{"run_id": run_id, "stage": "analyze", "params": json.dumps(params), "lexicon_hash": rules_hash(),
                         "n_items": len(pred), "n_auto": int((pred["route"] == "auto").sum()),
                         "n_review": int((pred["route"] == "review").sum()), "status": "SUCCEEDED",
                         "started_at": started.strftime(FMT), "finished_at": now}])
    out = {"pipeline_run": run, "feedback_item": items, "prediction": pred[columns("prediction")],
           "data_exception": exc[columns("data_exception")]}

    # self-check: the pipeline's own output must satisfy the same contract as its input
    as_str = {t: d.astype(object).where(d.notna(), "").astype(str) for t, d in out.items()}
    bad = run_checks(as_str, only={"REQUIRED_MISSING", "TYPE_INVALID", "ENUM_INVALID", "ID_FORMAT", "PK_DUPLICATE"})
    if len(bad):
        raise RuntimeError(f"analysis output violates the contract:\n{bad.head(10).to_string()}")
    if not pred["confidence"].between(0, 1).all():
        raise RuntimeError("confidence outside 0..1")

    with engine.begin() as c:
        c.execute(text("DELETE FROM app.prediction"))
        c.execute(text("DELETE FROM app.feedback_item"))
        c.execute(text("DELETE FROM app.data_exception WHERE detected_by = 'analysis'"))
        for t in ("pipeline_run", "feedback_item", "prediction", "data_exception"):
            copy_df(c, t, out[t].astype(object).where(out[t].notna(), None).replace({"": None}))
    ins = run_insights(engine, run_id, items, pred)
    return {"run_id": run_id, "items": items, "pred": pred, "exceptions": exc, "run": run.iloc[0].to_dict(), **ins}
