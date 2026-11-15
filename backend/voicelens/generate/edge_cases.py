"""Inject the 5 labelled edge cases AFTER the valid baseline. Input rows look normal; the label of what is
wrong lives only in ground_truth/anomalies.csv (with the decision the pipeline is expected to take).
Each type touches its own disjoint set of records, so detections can be scored per type.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .taxonomy import OUT_OF_TAXONOMY_THEME_ID

DT_FMT = "%Y-%m-%d %H:%M:%S"
PK = {"review": "review_id", "survey_response": "response_id", "support_message": "message_id"}


def inject(rng: np.random.Generator, t: dict[str, pd.DataFrame], gold: pd.DataFrame, n: int) -> pd.DataFrame:
    anomalies: list[dict] = []
    used: set[tuple[str, str]] = set()

    def pick(cands: pd.DataFrame, k: int) -> pd.DataFrame:
        keys = list(zip(cands["source_type"], cands["source_id"]))
        mask = np.array([key not in used for key in keys], dtype=bool)
        cands = cands[mask]
        chosen = cands.loc[np.sort(rng.choice(cands.index.to_numpy(), size=min(k, len(cands)), replace=False))]
        used.update(zip(chosen["source_type"], chosen["source_id"]))
        return chosen

    def record(issue, st, sid, detail, decision):
        anomalies.append({"issue_type": issue, "source_type": st, "source_id": sid, "detail": detail,
                          "expected_decision": decision})

    labels, ftheme = t["sentiment_label"], t["feedback_theme"]
    tagged = gold.merge(labels[["source_type", "source_id"]], on=["source_type", "source_id"])

    # 1. LABEL_CONTRADICTS_TEXT: input label flipped to positive on clearly negative English text, no note
    c = tagged[(tagged["sentiment"] == "negative") & (tagged["style"] == "plain") & (tagged["language"] == "en")]
    for _, g in pick(c, n).iterrows():
        m = (labels["source_type"] == g["source_type"]) & (labels["source_id"] == g["source_id"])
        labels.loc[m, ["sentiment", "label_note"]] = ["positive", ""]
        record("LABEL_CONTRADICTS_TEXT", g["source_type"], g["source_id"],
               f"input label=positive but text template {g['template_id']} is negative; no label_note",
               "flag_for_human_review")

    # 2. DUPLICATE_RESPONSE: same customer + survey + text resubmitted 3 minutes later under a new RESP id
    resp = t["survey_response"]
    c = gold[(gold["source_type"] == "survey_response") & (gold["split"] == "train")]
    new_rows, new_gold = [], []
    next_counter = resp.groupby("survey_id").size().to_dict()
    for _, g in pick(c, n).iterrows():
        orig = resp[resp["response_id"] == g["source_id"]].iloc[0].to_dict()
        sid = orig["survey_id"]
        next_counter[sid] += 1
        dup = dict(orig, response_id=f"RESP-{sid}-{next_counter[sid]:03d}",
                   submitted_at=(datetime.strptime(orig["submitted_at"], DT_FMT) + timedelta(minutes=3)).strftime(DT_FMT))
        new_rows.append(dup)
        new_gold.append(dict(g, source_id=dup["response_id"]))
        used.add(("survey_response", dup["response_id"]))
        record("DUPLICATE_RESPONSE", "survey_response", dup["response_id"],
               f"duplicate of {orig['response_id']} (same customer, survey and text, +3 min)",
               "drop_duplicate_keep_first")
    t["survey_response"] = pd.concat([resp, pd.DataFrame(new_rows)], ignore_index=True)

    # 3. PII_LEAK: the customer's own (synthetic) name / email / phone written into the text
    cust = t["customer"].set_index("customer_id")
    ticket_customer = t["support_ticket"].set_index("ticket_id")["customer_id"]
    c = gold[gold["language"] == "en"]
    for _, g in pick(c, n).iterrows():
        df = t[g["source_type"]]
        i = df.index[df[PK[g["source_type"]]] == g["source_id"]][0]
        cid = (ticket_customer[df.at[i, "ticket_id"]] if g["source_type"] == "support_message"
               else df.at[i, "customer_id"])
        p = cust.loc[cid]
        df.at[i, "text"] = f"{df.at[i, 'text']} You can reach me at {p['email']} or {p['phone']}. - {p['display_name']}"
        record("PII_LEAK", g["source_type"], g["source_id"], f"text contains name/email/phone of {cid}",
               "redact_before_analysis")

    # 4. THEME_OUTSIDE_TAXONOMY: an input theme link to a theme id that does not exist
    c = tagged.drop_duplicates(["source_type", "source_id"])
    extra = []
    for _, g in pick(c, n).iterrows():
        at = labels.loc[(labels["source_type"] == g["source_type"]) & (labels["source_id"] == g["source_id"]),
                        "labeled_at"].iloc[0]
        extra.append({"source_type": g["source_type"], "source_id": g["source_id"],
                      "theme_id": OUT_OF_TAXONOMY_THEME_ID, "labeler": "source_system", "tagged_at": at})
        record("THEME_OUTSIDE_TAXONOMY", g["source_type"], g["source_id"],
               f"feedback_theme links to {OUT_OF_TAXONOMY_THEME_ID}, which is not in the taxonomy",
               "reject_link_and_log_exception")
    t["feedback_theme"] = pd.concat([ftheme, pd.DataFrame(extra)], ignore_index=True)

    # 5. TEST_LABEL_IN_MODEL_INPUT: an eval item's evaluation label copied into its input `tags` column
    c = gold[(gold["split"] == "eval") & gold["source_type"].isin(["review", "survey_response"])]
    for _, g in pick(c, n).iterrows():
        df = t[g["source_type"]]
        i = df.index[df[PK[g["source_type"]]] == g["source_id"]][0]
        old = df.at[i, "tags"]
        old = "" if pd.isna(old) else old
        df.at[i, "tags"] = ";".join(x for x in (old, f"eval_label={g['sentiment']}") if x)
        record("TEST_LABEL_IN_MODEL_INPUT", g["source_type"], g["source_id"],
               "eval-split label copied into input column tags", "strip_tag_and_exclude_from_eval")

    _append_gold(gold, pd.DataFrame(new_gold))
    out = pd.DataFrame(anomalies)
    out.insert(0, "anomaly_id", [f"ANOM-{k:04d}" for k in range(1, len(out) + 1)])
    return out


def _append_gold(gold: pd.DataFrame, rows: pd.DataFrame) -> None:
    """Append rows to `gold` in place (duplicates keep the labels of the record they copy)."""
    for _, r in rows.iterrows():
        gold.loc[len(gold)] = r
