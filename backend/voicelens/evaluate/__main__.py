"""CLI: python -m voicelens.evaluate [--data data/output] [--target 0.95]      (run from backend/)
Compares the pipeline's DB outputs with data/output/ground_truth/ and writes
<data>/evaluation/{metrics.json, EVALUATION.md}. The eval split is reported; tau is chosen on the train split."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from sqlalchemy import text

from ..db.engine import get_engine
from ..db.load import copy_df
from ..db.models import TABLES, metadata
from ..generate.contract import columns
from ..generate.__main__ import DEFAULT_OUT
from . import metrics as M

SAMPLE_PER_CLASS = 25    # 4 sentiments x 25 = 100 items for blind human review

EXPECTED = {  # expected_decision -> how we verify the pipeline took it
    "flag_for_human_review": "exception FLAG + prediction routed to review",
    "drop_duplicate_keep_first": "exception QUARANTINE + item excluded from analysis",
    "redact_before_analysis": "exception + PII removed from the analysed text",
    "reject_link_and_log_exception": "exception QUARANTINE on the theme link",
    "strip_tag_and_exclude_from_eval": "exception QUARANTINE + item excluded from analysis",
}


def _read(engine, sql):
    with engine.connect() as c:
        return pd.read_sql(sql, c)


def evaluate(data: Path, target: float = 0.95) -> dict:
    gt_dir = Path(data) / "ground_truth"
    labels = pd.read_csv(gt_dir / "labels.csv", dtype=str, keep_default_na=False)
    inc = pd.read_csv(gt_dir / "incidents.csv", dtype={"lag_support_days": int, "lag_review_days": int,
                                                       "lag_survey_days": int}, keep_default_na=False)
    anom = pd.read_csv(gt_dir / "anomalies.csv", dtype=str, keep_default_na=False)
    e = get_engine()
    pred = _read(e, "SELECT p.*, f.redacted_text, f.pii_count FROM app.prediction p "
                    "JOIN app.feedback_item f USING (source_type, source_id)")
    run = _read(e, "SELECT * FROM app.pipeline_run ORDER BY run_id DESC LIMIT 1").iloc[0].to_dict()
    exc = _read(e, "SELECT * FROM app.data_exception")
    alerts = _read(e, "SELECT * FROM app.alert")
    for c in ("start_date", "detected_date", "peak_date", "end_date", "first_support_date", "first_review_date",
              "first_survey_date"):
        alerts[c] = alerts[c].astype(str).replace({"None": "", "NaT": ""})
    theme = _read(e, "SELECT theme_id, parent_theme_id FROM raw.theme")
    reviews = _read(e, "SELECT * FROM app.label_review_event")

    d = pred.merge(labels, on=["source_type", "source_id"], suffixes=("", "_gold"))
    d["ok"] = d["sentiment"] == d["sentiment_gold"]
    d["theme_ok"] = [set(a.split("|")) - {""} == set(b.split("|")) - {""}
                     for a, b in zip(d["theme_ids"].fillna(""), d["theme_ids_gold"])]
    d["auto"] = d["route"] == "auto"
    other = d["route_reason"].fillna("").str.replace("LOW_CONFIDENCE", "").str.strip("|") != ""
    d["other_reason"] = other

    res = {"evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "run_id": run["run_id"],
           "rules_hash": run["lexicon_hash"], "params": json.loads(run["params"]), "splits": {}}
    for split in ("train", "eval"):
        s = d[d["split"] == split]
        n_gold = int((labels["split"] == split).sum())
        curve = M.coverage_curve(s["confidence"], s["other_reason"], s["ok"])
        res["splits"][split] = {
            "gold_items": n_gold, "evaluated_items": len(s), "excluded_items": n_gold - len(s),
            "sentiment_all": M.classification(s["sentiment_gold"], s["sentiment"]),
            "sentiment_auto": M.classification(s.loc[s["auto"], "sentiment_gold"], s.loc[s["auto"], "sentiment"]),
            "coverage": round(float(s["auto"].mean()), 4),
            "themes": M.theme_sets(s["theme_ids_gold"], s["theme_ids"]),
            "by_style": M.slices(s, "style"), "by_language": M.slices(s, "language"),
            "by_source": M.slices(s, "source_type"), "coverage_curve": curve}
    tau = M.choose_tau(res["splits"]["train"]["coverage_curve"], target)
    on_eval = next(c for c in res["splits"]["eval"]["coverage_curve"] if c["tau"] == tau["tau"])
    res["tau"] = {"rule": f"max train coverage with auto accuracy >= {target}", "current": res["params"]["tau"],
                  "recommended": tau["tau"], "train": tau, "eval": on_eval}

    # edge cases: recall/precision per planted type + was the expected decision taken?
    feedback_ids = set(zip(pred["source_type"], pred["source_id"]))
    ex = exc.assign(key=list(zip(exc["exception_type"], exc["source_type"], exc["source_id"])))
    rows = []
    for t, g in anom.groupby("issue_type"):
        hits = ex[ex["exception_type"] == t]
        found = [(t, r.source_type, r.source_id) in set(hits["key"]) for r in g.itertuples()]
        ok = []
        for r, f in zip(g.itertuples(), found):
            item = (r.source_type, r.source_id)
            h = hits[(hits["source_type"] == r.source_type) & (hits["source_id"] == r.source_id)]
            if not f:
                ok.append(False)
            elif r.expected_decision == "flag_for_human_review":
                p = pred[(pred["source_type"] == r.source_type) & (pred["source_id"] == r.source_id)]
                ok.append(len(p) == 1 and p.iloc[0]["route"] == "review")
            elif r.expected_decision in ("drop_duplicate_keep_first", "strip_tag_and_exclude_from_eval"):
                ok.append((h["disposition"] == "QUARANTINE").any() and item not in feedback_ids)
            elif r.expected_decision == "redact_before_analysis":
                p = pred[(pred["source_type"] == r.source_type) & (pred["source_id"] == r.source_id)]
                ok.append(len(p) == 1 and "@" not in p.iloc[0]["redacted_text"] and p.iloc[0]["pii_count"] > 0)
            else:
                ok.append((h["disposition"] == "QUARANTINE").any())
        flagged = hits.drop_duplicates(["source_type", "source_id"])
        rows.append({"issue_type": t, "planted": len(g), "detected": int(sum(found)),
                     "recall": round(sum(found) / len(g), 4), "flagged_total": len(flagged),
                     "precision": round(sum(found) / max(len(flagged), 1), 4),
                     "expected_decision": g["expected_decision"].iloc[0], "check": EXPECTED[g["expected_decision"].iloc[0]],
                     "decision_correct": int(sum(ok))})
    res["edge_cases"] = rows

    parent = dict(zip(theme["theme_id"], theme["parent_theme_id"]))
    per_inc, false = M.match_incidents(inc, alerts, parent)
    det = [r for r in per_inc if r["detected"]]
    res["incidents"] = {"incidents": len(per_inc), "detected": len(det),
                        "detection_rate": round(len(det) / max(len(per_inc), 1), 4),
                        "false_alarms": len(false), "false_alarm_list": false,
                        "recoveries": int((alerts["kind"] == "recovery").sum()) if len(alerts) else 0,
                        "mean_time_to_detect_days": round(sum(r["time_to_detect_days"] for r in det) / len(det), 2) if det else None,
                        "lead_channel_correct": sum(bool(r["lead_channel_correct"]) for r in det), "per_incident": per_inc}
    for r in det:   # how much of the alert's evidence was really caused by the incident
        ev = _read(e, f"SELECT source_type, source_id FROM app.alert_evidence WHERE alert_id = '{r['alert_id']}'")
        m = ev.merge(labels[["source_type", "source_id", "incident_id"]], on=["source_type", "source_id"], how="left")
        r["evidence_precision"] = round(float((m["incident_id"] == r["incident_id"]).mean()), 4) if len(m) else None

    # human-reviewed evaluation set: a blind, stratified sample of the eval split (no label exposed to the API/UI)
    in_db = labels[labels["split"] == "eval"].merge(pred[["source_type", "source_id"]], on=["source_type", "source_id"])
    sample = M.review_sample(in_db[["source_type", "source_id", "sentiment"]], per_class=SAMPLE_PER_CLASS)
    with e.begin() as c:
        metadata.create_all(c, tables=[TABLES["eval_review_sample"]], checkfirst=True)
        c.execute(text("DELETE FROM app.eval_review_sample"))
        copy_df(c, "eval_review_sample", sample[columns("eval_review_sample")])
    res["human_review"] = {"events": len(reviews), "sample_size": len(sample), "reviewed": 0}
    if len(reviews):
        h = reviews.sort_values(["event_at", "event_id"]).drop_duplicates(["source_type", "source_id"], keep="last")
        h = h.merge(sample, on=["source_type", "source_id"]).merge(
            pred[["source_type", "source_id", "sentiment", "theme_ids"]], on=["source_type", "source_id"]).merge(
            labels[["source_type", "source_id", "sentiment", "theme_ids"]].rename(
                columns={"sentiment": "gold", "theme_ids": "gold_themes"}), on=["source_type", "source_id"])
        if len(h):
            human_themes = h["new_theme_ids"].replace("-", "")
            res["human_review"].update({
                "reviewed": len(h),
                "model_vs_human": M.classification(h["new_sentiment"], h["sentiment"]),
                "model_vs_human_themes": M.theme_sets(human_themes, h["theme_ids"]),
                "human_vs_gold": round(float((h["new_sentiment"] == h["gold"]).mean()), 4),
                "overridden": int((h["decision"] == "overridden").sum())})
    out = Path(data) / "evaluation"
    out.mkdir(exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    (out / "EVALUATION.md").write_text(report(res), encoding="utf-8", newline="\n")
    return res


def _pct(x):
    return "-" if x is None else f"{x:.1%}"


def report(r: dict) -> str:
    ev, tr = r["splits"]["eval"], r["splits"]["train"]
    L = [f"# VoiceLens evaluation", "", f"Run `{r['run_id']}` · rules `{r['rules_hash']}` · evaluated {r['evaluated_at']}. "
         "Rules were tuned on TRAIN only; EVAL is the honest number.", "",
         "## Sentiment", "", "| Split | Items | Accuracy | Macro-F1 | Coverage (auto) | Auto accuracy | Theme exact | Theme micro-F1 |",
         "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, s in (("eval", ev), ("train (tuned on)", tr)):
        L.append(f"| {name} | {s['evaluated_items']:,} | {_pct(s['sentiment_all']['accuracy'])} | {s['sentiment_all']['macro_f1']:.3f} | "
                 f"{_pct(s['coverage'])} | {_pct(s['sentiment_auto']['accuracy'])} | {_pct(s['themes']['exact_match'])} | "
                 f"{s['themes']['micro_f1']:.3f} |")
    L += ["", f"Eval items excluded by the ingest gate (quarantined): {ev['excluded_items']}.", "",
          "Confusion matrix (eval, rows = gold, columns = predicted):", "",
          "| gold \\ pred | " + " | ".join(ev["sentiment_all"]["confusion"]["labels"]) + " |", "|---|---:|---:|---:|---:|"]
    for lab, row in zip(ev["sentiment_all"]["confusion"]["labels"], ev["sentiment_all"]["confusion"]["matrix"]):
        L.append(f"| {lab} | " + " | ".join(map(str, row)) + " |")
    for title, key, col in (("By style (eval)", "by_style", "style"), ("By language (eval)", "by_language", "language")):
        L += ["", f"## {title}", "", "| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |", "|---|---:|---:|---:|---:|---:|"]
        L += [f"| {x[col]} | {x['n']} | {_pct(x['accuracy'])} | {_pct(x['coverage'])} | {_pct(x['auto_accuracy'])} | "
              f"{_pct(x['theme_exact'])} |" for x in ev[key]]
    t = r["tau"]
    L += ["", "## Accuracy vs coverage (abstention threshold tau)", "",
          f"Rule: {t['rule']}. Current tau {t['current']} -> recommended **{t['recommended']}** "
          f"(train: coverage {_pct(t['train']['coverage'])}, auto accuracy {_pct(t['train']['auto_accuracy'])}; "
          f"eval: coverage {_pct(t['eval']['coverage'])}, auto accuracy {_pct(t['eval']['auto_accuracy'])}).", "",
          "| tau | Eval coverage | Eval auto accuracy |", "|---:|---:|---:|"]
    L += [f"| {c['tau']} | {_pct(c['coverage'])} | {_pct(c['auto_accuracy'])} |" for c in ev["coverage_curve"]]
    L += ["", "## Edge cases (planted vs detected)", "", "| Issue type | Planted | Detected | Recall | Precision | Expected decision | Decision correct |",
          "|---|---:|---:|---:|---:|---|---:|"]
    L += [f"| {x['issue_type']} | {x['planted']} | {x['detected']} | {_pct(x['recall'])} | {_pct(x['precision'])} | "
          f"{x['expected_decision']} | {x['decision_correct']}/{x['planted']} |" for x in r["edge_cases"]]
    i = r["incidents"]
    L += ["", "## Incident detection (early warning)", "",
          f"Detected **{i['detected']}/{i['incidents']}**, false alarms **{i['false_alarms']}**, recoveries {i['recoveries']}, "
          f"mean time-to-detect **{i['mean_time_to_detect_days']} days**, lead channel correct {i['lead_channel_correct']}/{i['detected']}.", "",
          "| Incident | Direction | Onset | Alert | Detected | Days | Lead | Lag support/review/survey (measured vs designed) | Evidence precision |",
          "|---|---|---|---|---|---:|---|---|---:|"]
    for x in i["per_incident"]:
        if x["detected"]:
            lag = " / ".join(f"{x[f'{c}_lag_measured'] if x[f'{c}_lag_measured'] is not None else '-'} vs {x[f'{c}_lag_designed']}"
                             for c in ("support", "review", "survey"))
            L.append(f"| {x['incident_id']} | {x['direction']} | {x['onset_date']} | {x['alert_id']} | {x['detected_date']} | "
                     f"{x['time_to_detect_days']} | {x['lead_channel']} | {lag} | {_pct(x['evidence_precision'])} |")
        else:
            L.append(f"| {x['incident_id']} | {x['direction']} | {x['onset_date']} | - | not detected | - | - | - | - |")
    h = r["human_review"]
    L += ["", "## Human-reviewed evaluation set", "",
          f"Blind sample of {h['sample_size']} eval items (stratified by gold sentiment, label hidden from reviewers). "
          f"Reviewed so far: **{h['reviewed']}** ({h['events']} review events in total)."]
    if h["reviewed"]:
        mh = h["model_vs_human"]
        L += ["", f"- Model vs human labels: accuracy **{_pct(mh['accuracy'])}**, macro-F1 {mh['macro_f1']:.3f} "
                  f"(n = {mh['n']}); themes exact {_pct(h['model_vs_human_themes']['exact_match'])}",
              f"- Human vs generator gold: agreement {_pct(h['human_vs_gold'])}; reviewer overrode the model on "
              f"{h['overridden']} items"]
    else:
        L.append("Open the Review queue -> 'Evaluation set' tab to label them; rerun evaluation to fill this section.")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VoiceLens evaluation vs ground truth")
    ap.add_argument("--data", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--target", type=float, default=0.95, help="target auto accuracy for choosing tau (train)")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    evaluate(a.data, a.target)
    print((a.data / "evaluation" / "EVALUATION.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
