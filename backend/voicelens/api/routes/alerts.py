"""/alerts, /alerts/{id}, /lineage/{kind}/{id} - the 'Why this number?' chain."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from .. import db

router = APIRouter(tags=["alerts & lineage"])

ALERT_SQL = """
SELECT a.*, pr.name AS product_name, t.code AS theme_code, t.name AS theme_name, ai.action_item_id
FROM app.alert a JOIN raw.product pr USING (product_id) JOIN raw.theme t USING (theme_id)
LEFT JOIN app.action_item ai ON ai.alert_id = a.alert_id
"""


@router.get("/alerts")
def list_alerts(direction: str | None = None, status: str | None = None):
    return db.rows(ALERT_SQL + " WHERE (CAST(:d AS text) IS NULL OR a.direction = :d) "
                   "AND (CAST(:s AS text) IS NULL OR a.status = :s) ORDER BY a.detected_date", d=direction, s=status)


def _alert(alert_id: str) -> dict:
    a = db.one(ALERT_SQL + " WHERE a.alert_id = :a", a=alert_id)
    if not a:
        raise HTTPException(404, f"alert {alert_id} not found")
    return a


def _evidence(alert_id: str, limit: int = 200) -> list[dict]:
    return db.rows(db.ITEM_SQL.replace("SELECT ", "SELECT e.role, ", 1) +
                   " JOIN app.alert_evidence e ON e.source_type = f.source_type AND e.source_id = f.source_id "
                   "WHERE e.alert_id = :a ORDER BY f.event_at LIMIT :n", a=alert_id, n=limit)


@router.get("/alerts/{alert_id}")
def alert_detail(alert_id: str):
    a = _alert(alert_id)
    series = db.rows("""
        SELECT f.event_at::date AS day, f.channel_type, count(*) AS n,
               sum((p.sentiment = 'negative')::int) AS negatives
        FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)
        WHERE f.product_id = :pid AND :tid = ANY(string_to_array(p.theme_ids, '|'))
          AND f.event_at::date BETWEEN CAST(:lo AS date) - 35 AND CAST(:hi AS date) + 14
        GROUP BY 1, 2 ORDER BY 1, 2""", pid=a["product_id"], tid=a["theme_id"], lo=a["start_date"], hi=a["end_date"])
    return {"alert": a, "daily_series": series, "evidence": _evidence(alert_id)}


@router.get("/lineage/{kind}/{obj_id}")
def lineage(kind: str, obj_id: str):
    """kind = action | alert | cell. Returns the chain from the number down to the source records."""
    chain = []
    if kind == "action":
        act = db.one("SELECT * FROM app.action_item WHERE action_item_id = :i", i=obj_id)
        if not act:
            raise HTTPException(404, f"action item {obj_id} not found")
        inputs = json.loads(act["priority_inputs"])
        chain.append({"level": "action_item", "id": obj_id, "priority_score": act["priority_score"],
                      "formula": "volume x neg_share x severity_weight x (1 + shift)", "inputs": inputs,
                      "rule": act["created_from_rule"], "recommendation": act["recommendation"]})
        if not act["alert_id"]:
            ids = act["evidence_ids"].split("|")[:200]
            items = db.rows(db.ITEM_SQL + " WHERE f.source_id = ANY(:ids) ORDER BY f.event_at", ids=ids)
            return {"chain": chain, "items": items}
        kind, obj_id = "alert", act["alert_id"]
    if kind == "alert":
        a = _alert(obj_id)
        chain.append({"level": "alert", "id": obj_id, "detected_date": a["detected_date"], "peak_z": a["peak_z"],
                      "baseline_share": a["baseline_share"], "window_share": a["window_share"],
                      "lead_channel": a["lead_channel"], "test": "7-day window vs 28-day baseline, exact Poisson p<=1e-5, 3-day persistence"})
        return {"chain": chain, "items": _evidence(obj_id)}
    if kind == "cell":
        c = db.one("SELECT * FROM app.weekly_cell WHERE cell_id = :c", c=obj_id)
        if not c:
            raise HTTPException(404, f"cell {obj_id} not found")
        chain.append({"level": "weekly_cell", **c})
        items = db.rows(db.ITEM_SQL + " JOIN app.cell_member m ON m.source_type = f.source_type AND m.source_id = f.source_id "
                        "WHERE m.cell_id = :c ORDER BY f.event_at", c=obj_id)
        return {"chain": chain, "items": items}
    raise HTTPException(400, "kind must be action, alert or cell")
