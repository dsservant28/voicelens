"""/health, /meta, /overview."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.exc import SQLAlchemyError

from ...generate.contract import TRANSITIONS
from .. import db

router = APIRouter(tags=["overview"])
HINT = "Run the pipeline first:  cd backend && python -m voicelens.pipeline --scale 0.25"


@router.get("/health")
def health():
    try:
        n = db.scalar("SELECT count(*) FROM app.prediction")
        return {"status": "ok", "database": "ok", "data_loaded": bool(n), "items": n, "hint": None if n else HINT}
    except SQLAlchemyError as e:
        return {"status": "degraded", "database": type(e).__name__, "data_loaded": False, "hint": HINT}


@router.get("/meta")
def meta():
    return {"products": db.rows("SELECT product_id, name, category FROM raw.product ORDER BY product_id"),
            "themes": db.rows("SELECT theme_id, code, name, parent_theme_id, severity_weight FROM raw.theme ORDER BY theme_id"),
            "channels": db.rows("SELECT channel_id, name, channel_type FROM raw.channel ORDER BY channel_id"),
            "run": db.one("SELECT * FROM app.pipeline_run ORDER BY run_id DESC LIMIT 1"),
            "action_transitions": sorted([f or "", t] for f, t in TRANSITIONS["action_item_event"])}


@router.get("/overview")
def overview():
    k = db.one("""
        WITH x AS (SELECT f.event_at, p.sentiment, p.route FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)),
             last AS (SELECT max(event_at) AS m FROM x)
        SELECT count(*) AS items,
               avg((route = 'auto')::int) AS auto_coverage,
               avg((sentiment = 'negative')::int) FILTER (WHERE event_at > (SELECT m FROM last) - interval '28 days') AS neg_share_last_28d,
               avg((sentiment = 'negative')::int) FILTER (WHERE event_at <= (SELECT m FROM last) - interval '28 days'
                                                          AND event_at > (SELECT m FROM last) - interval '56 days') AS neg_share_prev_28d,
               (SELECT m FROM last) AS data_until
        FROM x""")
    k.update(db.one("""SELECT
        (SELECT count(*) FROM app.alert WHERE status = 'ACTIVE') AS active_alerts,
        (SELECT count(*) FROM app.alert) AS alerts,
        (SELECT count(*) FROM app.action_item WHERE status IN ('OPEN', 'IN_PROGRESS')) AS open_actions,
        (SELECT count(*) FROM app.prediction p WHERE route = 'review' AND NOT EXISTS (
            SELECT 1 FROM app.label_review_event r WHERE r.source_type = p.source_type AND r.source_id = p.source_id)) AS review_pending,
        (SELECT count(*) FROM app.data_exception) AS exceptions"""))
    trend = db.rows("""
        SELECT f.week_start, f.channel_type, count(*) AS n,
               round(avg((p.sentiment = 'negative')::int), 4) AS neg_share,
               round(avg((p.sentiment = 'positive')::int), 4) AS pos_share
        FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)
        GROUP BY 1, 2 ORDER BY 1, 2""")
    mix = db.rows("SELECT sentiment, count(*) AS n FROM app.prediction GROUP BY 1 ORDER BY 2 DESC")
    top = db.rows("""
        SELECT a.alert_id, a.kind, a.status, a.product_id, pr.name AS product_name, t.name AS theme_name,
               a.detected_date, a.peak_z, a.magnitude, a.shift, a.lead_channel, ai.action_item_id
        FROM app.alert a JOIN raw.product pr USING (product_id) JOIN raw.theme t USING (theme_id)
        LEFT JOIN app.action_item ai ON ai.alert_id = a.alert_id
        ORDER BY a.magnitude DESC LIMIT 5""")
    return {"kpis": k, "trend": trend, "sentiment_mix": mix, "top_alerts": top}
