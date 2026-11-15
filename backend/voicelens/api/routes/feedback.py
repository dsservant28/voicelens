"""/feedback/{source_type}/{id}, /review-queue, POST /review/{source_type}/{id} (append-only label_review_event)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import db

router = APIRouter(tags=["feedback & review"])
Sentiment = Literal["positive", "negative", "neutral", "mixed"]
SourceType = Literal["review", "survey_response", "support_message"]


def _item(source_type: str, source_id: str) -> dict:
    it = db.one(db.ITEM_SQL + " WHERE f.source_type = :st AND f.source_id = :sid", st=source_type, sid=source_id)
    if not it:
        raise HTTPException(404, f"{source_type} {source_id} not found (or quarantined at ingest)")
    return it


def _current(source_type: str, source_id: str, item: dict) -> tuple[str, str]:
    """Effective label = latest human review if any, else the model prediction."""
    last = db.one("SELECT new_sentiment, new_theme_ids FROM app.label_review_event WHERE source_type = :st "
                  "AND source_id = :sid ORDER BY event_at DESC, event_id DESC LIMIT 1", st=source_type, sid=source_id)
    if last:
        return last["new_sentiment"], last["new_theme_ids"]
    return item["sentiment"], item["theme_ids"] or "-"


@router.get("/feedback/{source_type}/{source_id}")
def feedback(source_type: SourceType, source_id: str):
    it = _item(source_type, source_id)
    return {"item": it,
            "themes": db.rows("SELECT theme_id, code, name FROM raw.theme WHERE theme_id = ANY(string_to_array(:t, '|'))",
                              t=it["theme_ids"] or ""),
            "exceptions": db.rows("SELECT exception_id, exception_type, disposition, detail, detected_by "
                                  "FROM app.data_exception WHERE source_type = :st AND source_id = :sid",
                                  st=source_type, sid=source_id),
            "reviews": db.rows("SELECT * FROM app.label_review_event WHERE source_type = :st AND source_id = :sid "
                               "ORDER BY event_at", st=source_type, sid=source_id)}


BLIND = ("sentiment", "confidence", "theme_ids", "route", "route_reason", "rules_fired", "evidence")


@router.get("/review-queue")
def review_queue(set: Literal["uncertain", "eval"] = "uncertain", reason: str | None = None,
                 status: Literal["pending", "reviewed", "all"] = "pending", limit: int = 50, offset: int = 0):
    """set=uncertain: items the model routed to review (with its prediction and reasons).
    set=eval: the blind human-review sample of the evaluation split - the model's answer is hidden."""
    reviewed = """(:status = 'all' OR (:status = 'pending') = NOT EXISTS (
             SELECT 1 FROM app.label_review_event r WHERE r.source_type = f.source_type AND r.source_id = f.source_id))"""
    params = {"reason": reason, "status": status}
    if set == "eval":
        join = " JOIN app.eval_review_sample s ON s.source_type = f.source_type AND s.source_id = f.source_id "
        where, order = " WHERE " + reviewed, " ORDER BY s.sample_rank"
    else:
        join, order = "", " ORDER BY p.confidence, f.source_id"
        where = """ WHERE p.route = 'review'
        AND (CAST(:reason AS text) IS NULL OR :reason = ANY(string_to_array(p.route_reason, '|'))) AND """ + reviewed
    total = db.scalar("SELECT count(*) FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)"
                      + join + where, **params)
    items = db.rows(db.ITEM_SQL + join + where + order + " LIMIT :lim OFFSET :off",
                    lim=min(limit, 200), off=offset, **params)
    if set == "eval":
        items = [{k: v for k, v in it.items() if k not in BLIND} for it in items]
    reasons = db.rows("SELECT r AS reason, count(*) AS n FROM app.prediction, "
                      "unnest(string_to_array(route_reason, '|')) r WHERE route = 'review' GROUP BY 1 ORDER BY 2 DESC")
    return {"set": set, "blind": set == "eval", "total": total, "items": items, "reasons": reasons}


class ReviewIn(BaseModel):
    sentiment: Sentiment
    theme_ids: list[str] = Field(default_factory=list, description="empty = keep current themes")
    reviewer: str = Field(min_length=1, max_length=80)


@router.post("/review/{source_type}/{source_id}", status_code=201)
def submit_review(source_type: SourceType, source_id: str, body: ReviewIn):
    it = _item(source_type, source_id)
    old_s, old_t = _current(source_type, source_id, it)
    if body.theme_ids:
        known = {r["theme_id"] for r in db.rows("SELECT theme_id FROM raw.theme")}
        bad = set(body.theme_ids) - known
        if bad:
            raise HTTPException(422, f"unknown theme ids: {sorted(bad)}")
    new_t = "|".join(body.theme_ids) if body.theme_ids else old_t
    decision = "confirmed" if (body.sentiment == old_s and new_t == old_t) else "overridden"
    n = db.scalar("SELECT coalesce(max(substr(event_id, 5)::int), 0) FROM app.label_review_event") + 1
    ev = {"event_id": f"LRE-{n:06d}", "st": source_type, "sid": source_id, "os": old_s, "ns": body.sentiment,
          "ot": old_t, "nt": new_t, "d": decision, "r": body.reviewer,
          "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    db.execute([("INSERT INTO app.label_review_event (event_id, source_type, source_id, old_sentiment, new_sentiment, "
                 "old_theme_ids, new_theme_ids, decision, reviewer, event_at) VALUES (:event_id, :st, :sid, :os, :ns, "
                 ":ot, :nt, :d, :r, :at)", ev)])
    return db.one("SELECT * FROM app.label_review_event WHERE event_id = :e", e=ev["event_id"])
