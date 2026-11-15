"""/data-quality, /flow (every row accounted for), /evaluation, POST /evaluation/run, POST /pipeline/run."""
from __future__ import annotations

import json
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from ...generate.__main__ import DEFAULT_OUT
from ...generate.contract import INPUT_TABLES
from .. import db

router = APIRouter(tags=["quality, evaluation & pipeline"])
SOURCE = {"review": "Reviews", "survey_response": "Survey responses", "support_message": "Support messages"}
REFERENCE = "Reference & events"


def _json(path, what: str):
    if not path.exists():
        raise HTTPException(404, f"{what} not found at {path}; run: python -m voicelens.pipeline")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/data-quality")
def data_quality(exception_type: str | None = None, limit: int = 100, offset: int = 0):
    summary = _json(DEFAULT_OUT / "validation" / "validation_summary.json", "validation summary")
    manifest = _json(DEFAULT_OUT / "manifest.json", "manifest")
    by_type = db.rows("SELECT exception_type, check_category, disposition, detected_by, count(*) AS n "
                      "FROM app.data_exception GROUP BY 1, 2, 3, 4 ORDER BY n DESC")
    total = db.scalar("SELECT count(*) FROM app.data_exception WHERE (CAST(:t AS text) IS NULL OR exception_type = :t)",
                      t=exception_type)
    items = db.rows("SELECT * FROM app.data_exception WHERE (CAST(:t AS text) IS NULL OR exception_type = :t) "
                    "ORDER BY exception_id LIMIT :l OFFSET :o", t=exception_type, l=min(limit, 500), o=offset)
    return {"summary": summary, "manifest": manifest, "by_type": by_type, "total": total, "exceptions": items}


@router.get("/flow")
def flow():
    """Sankey of every loaded row: source -> ingest gate (quarantined / flagged / clean) -> use -> routing.
    Reconciled here: rows in == rows out, and 'analysed' == app.feedback_item."""
    counts = {t: int(db.scalar(f"SELECT count(*) FROM raw.{t}")) for t in INPUT_TABLES}
    quar, flag = defaultdict(set), defaultdict(set)
    for e in db.rows("SELECT table_name, record_key, disposition FROM app.data_exception WHERE detected_by = 'validation'"):
        (quar if e["disposition"] == "QUARANTINE" else flag)[e["table_name"]].add(e["record_key"])
    agents = {r["message_id"] for r in db.rows("SELECT message_id FROM raw.support_message WHERE sender = 'agent'")}
    links: dict[tuple[str, str], int] = defaultdict(int)
    for t, n in counts.items():
        src = SOURCE.get(t, REFERENCE)
        q, f = quar[t], flag[t] - quar[t]
        c = n - len(q) - len(f)
        links[(src, "Quarantined")] += len(q)
        links[(src, "Flagged")] += len(f)
        links[(src, "Clean")] += c
        links[("Quarantined", "Excluded · audit only")] += len(q)
        if t in SOURCE:
            a_f = len(f & agents) if t == "support_message" else 0
            a_c = (len(agents) - len(agents & q) - a_f) if t == "support_message" else 0
            links[("Flagged", "Agent replies · context")] += a_f
            links[("Clean", "Agent replies · context")] += a_c
            links[("Flagged", "Analysed")] += len(f) - a_f
            links[("Clean", "Analysed")] += c - a_c
        else:
            links[("Flagged", "Reference data")] += len(f)
            links[("Clean", "Reference data")] += c
    routes = {r["route"]: int(r["n"]) for r in db.rows("SELECT route, count(*) AS n FROM app.prediction GROUP BY 1")}
    links[("Analysed", "Auto-labelled")] = routes.get("auto", 0)
    links[("Analysed", "Human review")] = routes.get("review", 0)
    analysed = links[("Flagged", "Analysed")] + links[("Clean", "Analysed")]
    feedback_items = int(db.scalar("SELECT count(*) FROM app.feedback_item"))
    terminal = ["Excluded · audit only", "Agent replies · context", "Reference data", "Auto-labelled", "Human review"]
    rows_in, rows_out = sum(counts.values()), sum(v for (s, t), v in links.items() if t in terminal)
    stage = {**{v: 0 for v in [*SOURCE.values(), REFERENCE]}, "Quarantined": 1, "Flagged": 1, "Clean": 1,
             "Excluded · audit only": 2, "Agent replies · context": 2, "Reference data": 2, "Analysed": 2,
             "Auto-labelled": 3, "Human review": 3}
    return {"nodes": [{"name": k, "stage": v} for k, v in stage.items()],
            "links": [{"source": s, "target": t, "value": v} for (s, t), v in links.items() if v > 0],
            "tables": counts,
            "reconciliation": {"rows_in": rows_in, "rows_out": rows_out, "balanced": rows_in == rows_out,
                               "analysed": analysed, "feedback_items": feedback_items,
                               "analysed_matches_items": analysed == feedback_items,
                               "routed": sum(routes.values()), "routed_matches_items": sum(routes.values()) == feedback_items}}


@router.get("/evaluation")
def evaluation():
    return _json(DEFAULT_OUT / "evaluation" / "metrics.json", "evaluation metrics")


@router.post("/evaluation/run")
def run_evaluation():
    """Recompute evaluation (incl. the human-reviewed set) from the current DB state - a few seconds."""
    from ...evaluate.__main__ import evaluate
    ev = evaluate(DEFAULT_OUT)
    return {"evaluated_at": ev["evaluated_at"], "human_reviewed": ev["human_review"]["reviewed"],
            "eval_accuracy": ev["splits"]["eval"]["sentiment_all"]["accuracy"]}


@router.post("/pipeline/run")
def run_pipeline(tau: float | None = None):
    """Admin: rerun analysis (stages 2-8) and evaluation on the loaded data. Idempotent; keeps human history."""
    from ...analyze.route import TAU
    from ...analyze.run import analyze
    from ...evaluate.__main__ import evaluate
    res = analyze(db.engine(), tau if tau is not None else TAU)
    ev = evaluate(DEFAULT_OUT)
    return {"run": res["run"], "alerts": len(res["alerts"]),
            "eval_accuracy": ev["splits"]["eval"]["sentiment_all"]["accuracy"],
            "incidents_detected": ev["incidents"]["detected"]}
