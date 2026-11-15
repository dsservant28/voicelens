"""/themes (ranked recurring themes = service priorities), /themes/{product}/{theme} (weekly cells),
/trend/items (the source records behind any trend point)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ...analyze.prioritize import score
from .. import db

router = APIRouter(tags=["themes, priorities & trends"])
WINDOW_WEEKS = 4


@router.get("/themes")
def ranked_themes(limit: int = 50):
    """Every product x theme over the last 4 weeks vs the 4 before, scored with the same priority formula as
    action items: volume x neg_share x severity_weight x (1 + shift). Built from weekly cells (traceable)."""
    rows = db.rows("""
        WITH last AS (SELECT max(week_start) AS m FROM app.weekly_cell),
        agg AS (
          SELECT c.product_id, c.theme_id,
                 sum(c.n_items) FILTER (WHERE c.week_start > l.m - 7 * :w) AS recent_n,
                 sum(c.n_negative) FILTER (WHERE c.week_start > l.m - 7 * :w) AS recent_neg,
                 sum(c.n_items) FILTER (WHERE c.week_start <= l.m - 7 * :w AND c.week_start > l.m - 14 * :w) AS prev_n,
                 sum(c.n_negative) FILTER (WHERE c.week_start <= l.m - 7 * :w AND c.week_start > l.m - 14 * :w) AS prev_neg,
                 sum(c.n_items) AS total_n, max(l.m) AS last_week
          FROM app.weekly_cell c CROSS JOIN last l GROUP BY 1, 2)
        SELECT a.*, pr.name AS product_name, t.code AS theme_code, t.name AS theme_name, t.severity_weight,
               (SELECT string_agg(alert_id, '|') FROM app.alert x WHERE x.product_id = a.product_id
                  AND x.theme_id = a.theme_id AND x.status = 'ACTIVE') AS active_alerts,
               (SELECT string_agg(action_item_id, '|') FROM app.action_item ai WHERE ai.product_id = a.product_id
                  AND ai.theme_id = a.theme_id AND ai.status IN ('OPEN', 'IN_PROGRESS')) AS open_actions
        FROM agg a JOIN raw.product pr USING (product_id) JOIN raw.theme t USING (theme_id)
        WHERE coalesce(a.recent_n, 0) > 0""", w=WINDOW_WEEKS)
    for r in rows:
        n, neg = int(r["recent_n"] or 0), int(r["recent_neg"] or 0)
        share = neg / n if n else 0.0
        prev = (int(r["prev_neg"] or 0) / int(r["prev_n"])) if r["prev_n"] else share
        r.update({"neg_share": round(share, 4), "prev_neg_share": round(prev, 4), "shift": round(share - prev, 4),
                  "priority": score(n, share, int(r["severity_weight"]), share - prev),
                  "formula": "volume x neg_share x severity_weight x (1 + max(shift, 0))"})
    rows.sort(key=lambda r: -r["priority"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows[:limit]


@router.get("/themes/{product_id}/{theme_id}")
def theme_detail(product_id: str, theme_id: str):
    cells = db.rows("SELECT * FROM app.weekly_cell WHERE product_id = :p AND theme_id = :t ORDER BY week_start, channel_type",
                    p=product_id, t=theme_id)
    if not cells:
        raise HTTPException(404, f"no feedback for {product_id} x {theme_id}")
    head = db.one("SELECT pr.name AS product_name, t.name AS theme_name, t.code AS theme_code, t.severity_weight "
                  "FROM raw.product pr, raw.theme t WHERE pr.product_id = :p AND t.theme_id = :t", p=product_id, t=theme_id)
    return {**head, "product_id": product_id, "theme_id": theme_id, "weekly_cells": cells,
            "alerts": db.rows("SELECT alert_id, kind, status, detected_date, peak_z FROM app.alert "
                              "WHERE product_id = :p AND theme_id = :t ORDER BY detected_date", p=product_id, t=theme_id)}


@router.get("/trend/items")
def trend_items(week_start: str, channel_type: str | None = None, product_id: str | None = None,
                theme_id: str | None = None, sentiment: str | None = None, limit: int = 50, offset: int = 0):
    """The source records behind one trend point (week [+ channel, product, theme, sentiment])."""
    where = """ WHERE f.week_start = CAST(:w AS date)
        AND (CAST(:c AS text) IS NULL OR f.channel_type = :c) AND (CAST(:p AS text) IS NULL OR f.product_id = :p)
        AND (CAST(:t AS text) IS NULL OR :t = ANY(string_to_array(p.theme_ids, '|')))
        AND (CAST(:s AS text) IS NULL OR p.sentiment = :s)"""
    params = {"w": week_start, "c": channel_type, "p": product_id, "t": theme_id, "s": sentiment}
    total = db.scalar("SELECT count(*) FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)"
                      + where, **params)
    items = db.rows(db.ITEM_SQL + where + " ORDER BY f.event_at, f.source_id LIMIT :lim OFFSET :off",
                    lim=min(limit, 200), off=offset, **params)
    return {"total": total, "items": items}
