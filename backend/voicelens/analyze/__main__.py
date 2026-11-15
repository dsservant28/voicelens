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
    print(f"\nweekly cells {len(res['cells']):,}  alerts {len(res['alerts'])}  "
          f"action items new {len(res['new_actions'])} / refreshed {len(res['updated_actions'])}")
    al = res["alerts"]
    if len(al):
        print(al[["alert_id", "product_id", "theme_id", "kind", "start_date", "detected_date", "end_date", "peak_z",
                  "lead_channel", "first_support_date", "first_review_date", "first_survey_date",
                  "evidence_count"]].to_string(index=False))
    print("\npriority candidates:")
    for c in res["candidates"][:10]:
        print(f"  {c['kind']:<8}{c['product_id']} {c['theme_id']}  priority {c['priority']:>7}  "
              f"vol {c['volume']:>3} neg {c['neg_share']:.0%} sev {c['severity_weight']} shift {c['shift']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
