"""Stage 5 - aggregate: one row per (item, theme) ('facts'), then the weekly cube product x theme x channel x week
with its member list (lineage). An item with two themes counts in both."""
from __future__ import annotations

import pandas as pd


def facts(items: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    f = items.merge(pred[["source_type", "source_id", "sentiment", "theme_ids"]], on=["source_type", "source_id"])
    f = f[f["theme_ids"].fillna("") != ""].assign(theme_id=lambda d: d["theme_ids"].str.split("|")).explode("theme_id")
    f["date"] = pd.to_datetime(f["event_at"]).dt.normalize()
    f["neg"] = (f["sentiment"] == "negative").astype(int)
    return f[["source_type", "source_id", "product_id", "theme_id", "channel_type", "date", "week_start", "neg",
              "score_norm"]].reset_index(drop=True)


def weekly(f: pd.DataFrame, run_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    f = f.assign(cell_id="CELL-" + f["week_start"].astype(str) + "-" + f["product_id"] + "-" + f["theme_id"] + "-"
                 + f["channel_type"])
    cells = (f.groupby(["cell_id", "week_start", "product_id", "theme_id", "channel_type"], as_index=False)
             .agg(n_items=("source_id", "size"), n_negative=("neg", "sum"), mean_score=("score_norm", "mean")))
    cells["neg_share"] = (cells["n_negative"] / cells["n_items"]).round(4)
    cells["mean_score"] = cells["mean_score"].round(4)
    cells["run_id"] = run_id
    members = f[["cell_id", "source_type", "source_id"]].drop_duplicates()
    return cells, members
