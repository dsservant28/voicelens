"""CLI: python -m voicelens.validate [--data data/output] [--no-repro]      (run from backend/)
Reads csv/ + manifest.json (never ground_truth/), runs every contract check, writes
<data>/validation/{data_exception.csv, validation_summary.json, validation_summary.md}. Never crashes on bad rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..generate.contract import INPUT_TABLES, columns
from ..generate.__main__ import DEFAULT_OUT
from .checks import CHECKS, run_checks
from .reproduce import reproducibility


def load_inputs(data: Path) -> dict[str, pd.DataFrame]:
    return {t: pd.read_csv(data / "csv" / f"{t}.csv", dtype=str, keep_default_na=False) for t in INPUT_TABLES}


def file_integrity(data: Path, manifest: dict, tables: dict[str, pd.DataFrame]) -> list[dict]:
    """Arithmetic reconciliation at file level: row counts and checksums vs manifest, columns vs contract."""
    out = []
    for f in manifest["files"]:
        if not f["path"].startswith("csv/"):
            continue
        t = Path(f["path"]).stem
        sha = hashlib.sha256((data / f["path"]).read_bytes()).hexdigest()
        out.append({"table": t, "rows_manifest": f["rows"], "rows_file": len(tables[t]),
                    "checksum_ok": sha == f["sha256"], "columns_ok": list(tables[t].columns) == columns(t),
                    "ok": sha == f["sha256"] and f["rows"] == len(tables[t]) and list(tables[t].columns) == columns(t)})
    return out


def validate(data: Path, repro: bool = True) -> dict:
    data = Path(data)
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    tables = load_inputs(data)
    integrity = file_integrity(data, manifest, tables)
    exc = run_checks(tables)
    now = datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
    exc.insert(0, "exception_id", [f"EXC-{i:06d}" for i in range(1, len(exc) + 1)])
    exc["detected_by"], exc["detected_at"], exc["resolution_status"] = "validation", now, "OPEN"
    exc = exc[columns("data_exception")]

    per_table = []
    for t in INPUT_TABLES:
        e = exc[exc["table_name"] == t]
        q = e[e["disposition"] == "QUARANTINE"]["record_key"].nunique()
        per_table.append({"table": t, "rows": len(tables[t]), "rows_with_exceptions": e["record_key"].nunique(),
                          "quarantined_rows": q, "clean_rows": len(tables[t]) - e["record_key"].nunique()})
    by_check = exc.groupby("check_name").size()
    checks = [{"check": c.name, "category": c.category, "disposition": c.disposition, "description": c.description,
               "exceptions": int(by_check.get(c.name, 0))} for c in CHECKS]
    by_type = (exc.groupby(["exception_type", "disposition"]).size().reset_index(name="count")
               .sort_values(["count", "exception_type"], ascending=[False, True]).to_dict("records"))
    rep = reproducibility(manifest["seed"], manifest["scale"], data / "manifest.json") if repro else None
    hard_fail = not all(i["ok"] for i in integrity) or (rep is not None and not rep["passed"])
    summary = {
        "status": "FAIL" if hard_fail else ("PASS_WITH_EXCEPTIONS" if len(exc) else "PASS"),
        "validated_at": now, "data_dir": str(data), "seed": manifest["seed"], "scale": manifest["scale"],
        "total_rows": int(sum(len(df) for df in tables.values())), "total_exceptions": len(exc),
        "quarantined_rows": int(sum(p["quarantined_rows"] for p in per_table)),
        "file_integrity": integrity, "tables": per_table, "checks": checks, "exceptions_by_type": by_type,
        "reproducibility": rep,
    }
    out = data / "validation"
    out.mkdir(exist_ok=True)
    exc.to_csv(out / "data_exception.csv", index=False, lineterminator="\n")
    (out / "validation_summary.json").write_text(json.dumps(summary, indent=2, default=int), encoding="utf-8")
    (out / "validation_summary.md").write_text(render_md(summary, exc), encoding="utf-8", newline="\n")
    return summary


def render_md(s: dict, exc: pd.DataFrame) -> str:
    L = [f"# Validation summary - {s['status']}", "",
         f"Data `{s['data_dir']}` · seed {s['seed']} · scale {s['scale']} · validated {s['validated_at']}  ",
         f"{s['total_rows']:,} rows checked · {s['total_exceptions']:,} exceptions · "
         f"{s['quarantined_rows']:,} rows quarantined (kept in DB, excluded from analysis)", "",
         "## Reproducibility", ""]
    r = s["reproducibility"]
    if r:
        L.append(f"Generated twice (seed {r['seed']}, scale {r['scale']}): {r['files_compared']} files, "
                 f"identical = **{r['runs_identical']}**; matches validated data = **{r.get('matches_validated_data', 'n/a')}** "
                 f"({r['seconds']} s).")
    else:
        L.append("Skipped (--no-repro).")
    L += ["", "## File integrity (manifest reconciliation)", "", "| Table | Rows (manifest) | Rows (file) | Checksum | Columns |",
          "|---|---:|---:|---|---|"]
    L += [f"| {i['table']} | {i['rows_manifest']:,} | {i['rows_file']:,} | {'ok' if i['checksum_ok'] else 'MISMATCH'} | "
          f"{'ok' if i['columns_ok'] else 'MISMATCH'} |" for i in s["file_integrity"]]
    L += ["", "## Tables", "", "| Table | Rows | With exceptions | Quarantined | Clean |", "|---|---:|---:|---:|---:|"]
    L += [f"| {t['table']} | {t['rows']:,} | {t['rows_with_exceptions']:,} | {t['quarantined_rows']:,} | {t['clean_rows']:,} |"
          for t in s["tables"]]
    L += ["", "## Exceptions by type", "", "| Exception type | Disposition | Count |", "|---|---|---:|"]
    L += [f"| {b['exception_type']} | {b['disposition']} | {b['count']:,} |" for b in s["exceptions_by_type"]]
    L += ["", "## Checks", "", "| Check | Category | Disposition | Exceptions | Rule |", "|---|---|---|---:|---|"]
    L += [f"| {c['check']} | {c['category']} | {c['disposition']} | {c['exceptions']:,} | {c['description']} |"
          for c in s["checks"]]
    if len(exc):
        L += ["", "## Examples (first 2 per type)", "", "| Exception | Table | Key | Detail |", "|---|---|---|---|"]
        for _, g in exc.groupby("exception_type"):
            L += [f"| {r.exception_type} | {r.table_name} | {r.record_key} | {r.detail} |" for r in g.head(2).itertuples()]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VoiceLens stage-1 ingest gate")
    ap.add_argument("--data", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-repro", action="store_true", help="skip the generate-twice reproducibility check")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    s = validate(a.data, repro=not a.no_repro)
    print((a.data / "validation" / "validation_summary.md").read_text(encoding="utf-8"))
    return 1 if s["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
