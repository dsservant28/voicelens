"""Stage 8 - act: rule-based action items with evidence. Upsert keyed by (product_id, theme_id, kind): a rerun refreshes
score/evidence/recommendation but never touches status or the append-only action_item_event history."""
from __future__ import annotations

import json

import pandas as pd

P_MIN, MIN_ALERT_DAYS = 10.0, 7
OWNER = {"delivery": "logistics_ops", "late_delivery": "logistics_ops", "billing": "billing_ops",
         "double_charge": "billing_ops", "refunds": "billing_ops", "pricing": "product_manager",
         "app_performance": "product_manager", "usability": "product_manager", "onboarding": "product_manager",
         "account_login": "product_manager", "product_quality": "product_manager", "customer_support": "support_lead"}
NEXT_STEP = {
    "delivery": "Review courier handling and packaging for {p}",
    "late_delivery": "Check carrier SLA and slot capacity for {p}",
    "billing": "Audit invoices and billing runs for {p}",
    "double_charge": "Check payment gateway for duplicate captures on {p}; refund affected customers",
    "refunds": "Review refund approval backlog and rejection reasons for {p}",
    "pricing": "Review price change communication and plan value for {p}",
    "app_performance": "Triage crash/latency reports for {p}; check the latest release",
    "usability": "Run a UX review of the confusing flows in {p}",
    "onboarding": "Fix setup/activation steps and docs for {p}",
    "account_login": "Investigate login/verification failures for {p}; check OTP delivery",
    "product_quality": "Open a quality investigation for {p} with the supplier",
    "customer_support": "Coach agents and review ticket handling for {p}",
}


def rule_text(c: dict) -> str:
    if c["kind"] == "alert":
        return f"ALERT_WORSEN({c['alert_id']}) duration>={MIN_ALERT_DAYS}d and priority>={P_MIN}"
    return "CHRONIC neg_share>=0.6 over 28d, volume>=15, priority>=%s" % P_MIN


def plan(cands: list[dict], existing: pd.DataFrame, theme_code: dict, product_name: dict, now: str,
         next_act: int, next_evt: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """-> (new action items, updates for existing items, new OPEN events)."""
    key = {(r.product_id, r.theme_id, r.kind): r.action_item_id for r in existing.itertuples()} if len(existing) else {}
    new, upd, evt = [], [], []
    for c in cands:
        if c["priority"] < P_MIN or (c["kind"] == "alert" and c["duration_days"] < MIN_ALERT_DAYS):
            continue
        code = theme_code[c["theme_id"]]
        row = {"theme_id": c["theme_id"], "product_id": c["product_id"], "priority_score": c["priority"],
               "owner_role": OWNER[code], "evidence_count": len(c["evidence"]), "evidence_ids": "|".join(c["evidence"]),
               "created_from_rule": rule_text(c), "kind": c["kind"], "alert_id": c["alert_id"],
               "priority_inputs": json.dumps({k: c[k] for k in ("volume", "neg_share", "severity_weight", "shift")}),
               "recommendation": NEXT_STEP[code].format(p=product_name[c["product_id"]])
               + f" ({c['volume']} items, {c['neg_share']:.0%} negative)", "updated_at": now}
        k = (c["product_id"], c["theme_id"], c["kind"])
        if k in key:
            upd.append({"action_item_id": key[k], **row})
        else:
            aid = f"ACT-{next_act:06d}"
            next_act += 1
            new.append({"action_item_id": aid, **row, "status": "OPEN", "created_at": now})
            evt.append({"event_id": f"AIE-{next_evt:06d}", "action_item_id": aid, "from_status": None,
                        "to_status": "OPEN", "actor": "system", "note": row["created_from_rule"], "event_at": now})
            next_evt += 1
    return pd.DataFrame(new), pd.DataFrame(upd), pd.DataFrame(evt)
