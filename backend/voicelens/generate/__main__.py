"""CLI: python -m voicelens.generate --scale 0.05 --seed 20261022 --out data/output   (run from backend/)"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .build import build
from .config import REFERENCE_DATE, SEED, WINDOW_END, WINDOW_START
from .contract import INPUT_TABLES
from .export import export

DEFAULT_OUT = Path(__file__).resolve().parents[3] / "data" / "output"


def generate(scale: float = 1.0, seed: int = SEED, out: Path = DEFAULT_OUT):
    tables, gt, vol = build(scale, seed)
    meta = {"generator": "voicelens.generate", "version": "1.0", "seed": seed, "scale": scale,
            "reference_date": REFERENCE_DATE.isoformat(),
            "window": [WINDOW_START.isoformat(), WINDOW_END.isoformat()],
            "command": f"python -m voicelens.generate --scale {scale} --seed {seed}",
            "volumes": asdict(vol)}
    manifest = export(tables, gt, out, meta)
    return tables, gt, manifest


def _summary(tables, gt, show: int, seed: int) -> None:
    print("\nRow counts")
    for t in INPUT_TABLES:
        print(f"  {t:<22}{len(tables[t]):>8,}")
    for k, df in gt.items():
        print(f"  ground_truth/{k:<9}{len(df):>8,}")
    labels = gt["labels"]
    print("\nGold sentiment share:", (labels["sentiment"].value_counts(normalize=True).round(3)).to_dict())
    print("Styles:", labels["style"].value_counts().to_dict())
    print("Languages:", labels["language"].value_counts().to_dict())
    print("Split:", labels["split"].value_counts().to_dict())
    print("Anomalies:", gt["anomalies"]["issue_type"].value_counts().to_dict())
    print("\nIncidents (signal start per channel, caused items)")
    for _, r in gt["incidents"].iterrows():
        print(f"  {r['incident_id']} {r['direction']:<7} {r['product_id']} {r['theme_id']} onset {r['onset_date']}"
              f" | support {r['support_signal_start']} review {r['review_signal_start']} survey {r['survey_signal_start']}"
              f" | items s/r/v = {r['n_support_items']}/{r['n_review_items']}/{r['n_survey_items']}")
    if show:
        text = pd.concat([tables[t].set_index(pk)["text"] for t, pk in
                          (("review", "review_id"), ("survey_response", "response_id"),
                           ("support_message", "message_id"))])
        print(f"\n{show} sample texts per style")
        for style, grp in labels.groupby("style"):
            print(f"\n[{style}]")
            for _, r in grp.sample(n=min(show, len(grp)), random_state=seed).iterrows():
                print(f"  {r['source_id']:<28} {r['language']:<7} {r['sentiment']:<8} {r['template_id']:<20} {text[r['source_id']]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VoiceLens synthetic data generator")
    ap.add_argument("--scale", type=float, default=1.0, help="1.0 = 50k reviews/responses + 20k messages")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--samples", type=int, default=0, help="print N sample texts per style")
    args = ap.parse_args(argv)
    tables, gt, manifest = generate(args.scale, args.seed, args.out)
    print(f"Wrote {len(manifest['files'])} files to {args.out} (seed {args.seed}, scale {args.scale})")
    _summary(tables, gt, args.samples, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
