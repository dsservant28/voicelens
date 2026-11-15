"""CLI: python -m voicelens.analyze [--tau 0.6]      (run from backend/; needs voicelens.db.load first)"""
from __future__ import annotations

import argparse
import sys

from ..db.engine import get_engine
from .route import TAU
from .run import analyze


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VoiceLens stages 2-4: normalize, analyze, abstain")
    ap.add_argument("--tau", type=float, default=TAU, help="confidence threshold for auto-labelling")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    res = analyze(get_engine(), a.tau)
    p, run = res["pred"], res["run"]
    print(f"{run['run_id']}  rules {run['lexicon_hash']}  items {run['n_items']:,}  "
          f"auto {run['n_auto']:,} ({run['n_auto'] / run['n_items']:.0%})  review {run['n_review']:,}")
    print("\nby source:", res["items"]["source_type"].value_counts().to_dict())
    print("sentiment:", p["sentiment"].value_counts().to_dict())
    print("language detected vs declared mismatches:",
          int((res["items"]["language_detected"] != res["items"]["language"]).sum()))
    print("no theme:", int((p["theme_ids"] == "").sum()))
    reasons = p["route_reason"].str.split("|").explode()
    print("review reasons:", reasons[reasons != ""].value_counts().to_dict())
    print("rules fired:", p["rules_fired"].str.split("|").explode().value_counts().to_dict())
    print("analysis exceptions:", res["exceptions"]["exception_type"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
