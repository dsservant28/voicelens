"""Stages 5-8: aggregate -> detect -> prioritize -> act, written in one transaction.
Cells/alerts are rebuilt each run (derived data); action items are upserted so human status history survives."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import Engine, text

from ..db.load import copy_df
from ..db.models import TABLES, metadata
from ..generate.contract import columns
from ..validate.checks import run_checks
from . import actions as A
from .aggregate import facts, weekly
from .detect import detect
from .prioritize import candidates

NEW_TABLES = ("weekly_cell", "cell_member", "alert", "alert_evidence")


def _null(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(object).where(df.notna(), None).replace({"": None})


def run_insights(engine: Engine, run_id: str, items: pd.DataFrame, pred: pd.DataFrame) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f = facts(items, pred)
    cells, members = weekly(f, run_id)
    alerts, evidence = detect(f, run_id)
    with engine.connect() as c:
        theme = pd.read_sql("SELECT theme_id, code, severity_weight FROM raw.theme", c)
        product = pd.read_sql("SELECT product_id, name FROM raw.product", c)
        existing = pd.read_sql("SELECT action_item_id, product_id, theme_id, kind FROM app.action_item", c)
        n_act = c.execute(text("SELECT coalesce(max(substr(action_item_id, 5)::int), 0) FROM app.action_item")).scalar_one()
        n_evt = c.execute(text("SELECT coalesce(max(substr(event_id, 5)::int), 0) FROM app.action_item_event")).scalar_one()
    cands = candidates(f, alerts, evidence, dict(zip(theme["theme_id"], theme["severity_weight"])))
    new, upd, evt = A.plan(cands, existing, dict(zip(theme["theme_id"], theme["code"])),
                           dict(zip(product["product_id"], product["name"])), now, n_act + 1, n_evt + 1)

    out = {"weekly_cell": cells[columns("weekly_cell")], "cell_member": members[columns("cell_member")],
           "alert": alerts[columns("alert")] if len(alerts) else pd.DataFrame(columns=columns("alert")),
           "alert_evidence": evidence[columns("alert_evidence")]}
    if len(new):
        out["action_item"] = new[columns("action_item")]
    if len(evt):
        out["action_item_event"] = evt[columns("action_item_event")]
    as_str = {t: d.astype(object).where(d.notna(), "").astype(str) for t, d in out.items()}
    bad = run_checks(as_str, only={"REQUIRED_MISSING", "TYPE_INVALID", "ENUM_INVALID", "ID_FORMAT", "PK_DUPLICATE"})
    if len(bad):
        raise RuntimeError(f"insight output violates the contract:\n{bad.head(10).to_string()}")

    with engine.begin() as c:
        metadata.create_all(c, tables=[TABLES[t] for t in NEW_TABLES], checkfirst=True)
        c.execute(text("UPDATE app.action_item SET alert_id = NULL"))
        for t in ("alert_evidence", "alert", "cell_member", "weekly_cell"):
            c.execute(text(f"DELETE FROM app.{t}"))
        for t in ("weekly_cell", "cell_member", "alert", "alert_evidence", "action_item", "action_item_event"):
            if t in out and len(out[t]):
                copy_df(c, t, _null(out[t]))
        if len(upd):
            cols = [k for k in upd.columns if k != "action_item_id"]
            sql = "UPDATE app.action_item SET " + ", ".join(f"{k} = :{k}" for k in cols) + \
                  " WHERE action_item_id = :action_item_id"
            c.execute(text(sql), _null(upd).to_dict("records"))
    return {"cells": cells, "alerts": alerts, "evidence": evidence, "candidates": cands, "new_actions": new,
            "updated_actions": upd}
