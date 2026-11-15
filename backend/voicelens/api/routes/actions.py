"""/action-items, POST /action-items/{id}/status - lifecycle checked against the data contract, history append-only."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...generate.contract import TRANSITIONS
from .. import db

router = APIRouter(tags=["action items"])

ACT_SQL = """
SELECT ai.*, pr.name AS product_name, t.name AS theme_name, t.code AS theme_code
FROM app.action_item ai JOIN raw.product pr USING (product_id) JOIN raw.theme t USING (theme_id)
"""


@router.get("/action-items")
def list_actions(status: str | None = None):
    return db.rows(ACT_SQL + " WHERE (CAST(:s AS text) IS NULL OR ai.status = :s) ORDER BY ai.priority_score DESC", s=status)


@router.get("/action-items/{action_item_id}")
def action_detail(action_item_id: str):
    a = db.one(ACT_SQL + " WHERE ai.action_item_id = :i", i=action_item_id)
    if not a:
        raise HTTPException(404, f"action item {action_item_id} not found")
    events = db.rows("SELECT * FROM app.action_item_event WHERE action_item_id = :i ORDER BY event_at, event_id",
                     i=action_item_id)
    allowed = sorted(t for f, t in TRANSITIONS["action_item_event"] if f == a["status"])
    return {"action_item": a, "events": events, "allowed_next": allowed}


class StatusIn(BaseModel):
    to_status: Literal["OPEN", "IN_PROGRESS", "DONE", "DISMISSED"]
    actor: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


@router.post("/action-items/{action_item_id}/status", status_code=201)
def change_status(action_item_id: str, body: StatusIn):
    a = db.one("SELECT status FROM app.action_item WHERE action_item_id = :i", i=action_item_id)
    if not a:
        raise HTTPException(404, f"action item {action_item_id} not found")
    if (a["status"], body.to_status) not in TRANSITIONS["action_item_event"]:
        raise HTTPException(409, f"illegal transition {a['status']} -> {body.to_status}")
    n = db.scalar("SELECT coalesce(max(substr(event_id, 5)::int), 0) FROM app.action_item_event") + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ev = {"e": f"AIE-{n:06d}", "i": action_item_id, "f": a["status"], "t": body.to_status, "a": body.actor,
          "n": body.note, "at": now}
    db.execute([
        ("INSERT INTO app.action_item_event (event_id, action_item_id, from_status, to_status, actor, note, event_at) "
         "VALUES (:e, :i, :f, :t, :a, :n, :at)", ev),
        ("UPDATE app.action_item SET status = :t, updated_at = :at WHERE action_item_id = :i", ev),  # derived = latest event
    ])
    return action_detail(action_item_id)
