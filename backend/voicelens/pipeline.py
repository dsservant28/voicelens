"""One command, fresh clone -> everything:  python -m voicelens.pipeline [--scale 0.25] [--no-repro]   (from backend/)
generate -> validate (+ reproducibility) -> load into PostgreSQL -> analyze (stages 2-8) -> evaluate.
Copies the validation and evaluation reports to docs/results/ so they can be read without running anything."""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from .db.engine import ENV_FILE, get_engine
from .generate.config import SEED
from .generate.__main__ import DEFAULT_OUT, generate

DOCS_RESULTS = Path(__file__).resolve().parents[2] / "docs" / "results"


def _check_db() -> None:
    try:
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
    except OperationalError as e:
        raise SystemExit(f"Cannot reach PostgreSQL via DATABASE_URL in {ENV_FILE}.\n"
                         f"Copy .env.example to .env, set DATABASE_URL, create the database, then retry.\n{e.orig}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the whole VoiceLens pipeline")
    ap.add_argument("--scale", type=float, default=0.25)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--no-repro", action="store_true", help="skip the generate-twice reproducibility check")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    _check_db()
    from .analyze.run import analyze
    from .db.load import load
    from .evaluate.__main__ import evaluate
    from .validate.__main__ import validate

    t0 = time.perf_counter()
    step = lambda msg: print(f"[{time.perf_counter() - t0:6.1f}s] {msg}", flush=True)
    step(f"1/5 generate  seed {a.seed}  scale {a.scale}")
    generate(a.scale, a.seed, DEFAULT_OUT)
    step("2/5 validate" + ("" if a.no_repro else " + reproducibility (generates twice)"))
    v = validate(DEFAULT_OUT, repro=not a.no_repro)
    step(f"    {v['status']}: {v['total_exceptions']} exceptions, {v['quarantined_rows']} rows quarantined")
    step("3/5 load into PostgreSQL (COPY)")
    rep = load(DEFAULT_OUT)
    step(f"    {sum(r['db_rows'] for r in rep):,} rows in {len(rep)} tables, counts match: {all(r['ok'] for r in rep)}")
    step("4/5 analyze: normalize -> sentiment/themes -> abstain -> aggregate -> detect -> prioritize -> act")
    res = analyze(get_engine())
    step(f"    {res['run']['run_id']}: {res['run']['n_items']:,} items, {res['run']['n_auto']:,} auto, "
         f"{len(res['alerts'])} alerts, {len(res['new_actions'])} new action items")
    step("5/5 evaluate vs ground truth")
    ev = evaluate(DEFAULT_OUT)
    s, i = ev["splits"]["eval"], ev["incidents"]
    step(f"    eval accuracy {s['sentiment_all']['accuracy']:.1%} (auto {s['sentiment_auto']['accuracy']:.1%} at "
         f"{s['coverage']:.0%} coverage), incidents {i['detected']}/{i['incidents']}, false alarms {i['false_alarms']}, "
         f"mean time-to-detect {i['mean_time_to_detect_days']} days")
    DOCS_RESULTS.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEFAULT_OUT / "validation" / "validation_summary.md", DOCS_RESULTS / "VALIDATION.md")
    shutil.copy(DEFAULT_OUT / "evaluation" / "EVALUATION.md", DOCS_RESULTS / "EVALUATION.md")
    step(f"reports copied to {DOCS_RESULTS}.  Next: uvicorn voicelens.api.main:app --reload  ->  http://localhost:8000/docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
