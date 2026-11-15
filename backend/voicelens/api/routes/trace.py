"""/pulse (daily signal per channel) and /trace/{id} (resolve ANY id to its lineage, up and down)."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from .. import db
from .alerts import lineage

router = APIRouter(tags=["pulse & trace"])
FEEDBACK = {"REV-": "review", "RESP-": "survey_response", "MSG-": "support_message"}


@router.get("/pulse")
def pulse():
    """Daily items and negatives per channel over the whole window (the seismograph traces)."""
    return db.rows("""
        SELECT f.event_at::date AS day, f.channel_type, count(*) AS n, sum((p.sentiment = 'negative')::int) AS negatives
        FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)
        GROUP BY 1, 2 ORDER BY 1, 2""")


@router.get("/trace/{obj_id}")
def trace(obj_id: str):
    """ACT-/ALR-/CELL- -> lineage down to records. REV-/RESP-/MSG- -> the record plus everything it feeds
    (weekly cells, alerts, action items) - the upward chain."""
    i = obj_id.strip().upper()
    if i.startswith("ACT-"):
        return {"kind": "action", "id": i, **lineage("action", i)}
    if i.startswith("ALR-"):
        return {"kind": "alert", "id": i, **lineage("alert", i)}
    if i.startswith("CELL-"):
        return {"kind": "cell", "id": obj_id.strip(), **lineage("cell", obj_id.strip())}
    st = next((v for k, v in FEEDBACK.items() if i.startswith(k)), None)
    if not st or not re.match(r"^[A-Z0-9-]+$", i):
        raise HTTPException(400, "unknown id format - try REV-, RESP-, MSG-, ALR-, ACT- or CELL- ids")
    item = db.one(db.ITEM_SQL + " WHERE f.source_type = :st AND f.source_id = :sid", st=st, sid=i)
    exceptions = db.rows("SELECT exception_id, exception_type, disposition, detail, detected_by FROM app.data_exception "
                         "WHERE source_type = :st AND source_id = :sid", st=st, sid=i)
    if not item:
        if exceptions:
            return {"kind": "record", "id": i, "quarantined": True, "item": None, "exceptions": exceptions,
                    "cells": [], "alerts": [], "actions": []}
        raise HTTPException(404, f"{i} not found")
    cells = db.rows("SELECT c.cell_id, c.week_start, c.theme_id, c.n_items, c.neg_share FROM app.cell_member m "
                    "JOIN app.weekly_cell c USING (cell_id) WHERE m.source_type = :st AND m.source_id = :sid", st=st, sid=i)
    alerts = db.rows("SELECT a.alert_id, a.kind, a.magnitude, a.detected_date, e.role FROM app.alert_evidence e "
                     "JOIN app.alert a USING (alert_id) WHERE e.source_type = :st AND e.source_id = :sid", st=st, sid=i)
    actions = db.rows("SELECT action_item_id, priority_score, status FROM app.action_item "
                      "WHERE :sid = ANY(string_to_array(evidence_ids, '|'))", sid=i)
    return {"kind": "record", "id": i, "quarantined": False, "item": item, "exceptions": exceptions,
            "cells": cells, "alerts": alerts, "actions": actions}
