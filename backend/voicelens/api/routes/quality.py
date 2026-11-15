"""/data-quality, /evaluation, POST /pipeline/run."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ...generate.__main__ import DEFAULT_OUT
from .. import db

router = APIRouter(tags=["quality, evaluation & pipeline"])


def _json(path, what: str):
    if not path.exists():
        raise HTTPException(404, f"{what} not found at {path}; run: python -m voicelens.pipeline")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/data-quality")
def data_quality(exception_type: str | None = None, limit: int = 100, offset: int = 0):
    summary = _json(DEFAULT_OUT / "validation" / "validation_summary.json", "validation summary")
    by_type = db.rows("SELECT exception_type, check_category, disposition, detected_by, count(*) AS n "
                      "FROM app.data_exception GROUP BY 1, 2, 3, 4 ORDER BY n DESC")
    items = db.rows("SELECT * FROM app.data_exception WHERE (CAST(:t AS text) IS NULL OR exception_type = :t) "
                    "ORDER BY exception_id LIMIT :l OFFSET :o", t=exception_type, l=min(limit, 500), o=offset)
    return {"summary": summary, "by_type": by_type, "exceptions": items}


@router.get("/evaluation")
def evaluation():
    return _json(DEFAULT_OUT / "evaluation" / "metrics.json", "evaluation metrics")


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
