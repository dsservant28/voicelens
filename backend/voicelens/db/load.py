"""CLI: python -m voicelens.db.load [--data data/output]      (run from backend/)
Idempotent bulk load: drop + recreate schemas raw/app from the contract, COPY every input CSV, load the validator's
data_exception rows, then add FKs NOT VALID. Rows the DB physically cannot hold (duplicate PK, bad type, missing
required, bad enum) are skipped here but stay documented in app.data_exception. Ground truth is never loaded."""
from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from ..generate.__main__ import DEFAULT_OUT
from ..generate.contract import INPUT_TABLES, columns
from ..validate.__main__ import load_inputs, validate
from .engine import get_engine
from .models import APP, RAW, TABLES, foreign_keys, metadata, schema_of

UNLOADABLE = {"PK_DUPLICATE", "TYPE_INVALID", "REQUIRED_MISSING", "ENUM_INVALID"}


def _copy(conn, table: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, lineterminator="\n")   # '' -> unquoted empty -> NULL
    cols = ", ".join(df.columns)
    with conn.connection.driver_connection.cursor() as cur:
        with cur.copy(f"COPY {schema_of(table)}.{table} ({cols}) FROM STDIN WITH (FORMAT csv)") as cp:
            cp.write(buf.getvalue())


def load(data: Path = DEFAULT_OUT) -> list[dict]:
    data = Path(data)
    exc_file = data / "validation" / "data_exception.csv"
    if not exc_file.exists():
        print("no validation output found -> running the validator first (--no-repro)")
        validate(data, repro=False)
    exc = pd.read_csv(exc_file, dtype=str, keep_default_na=False)
    tables = load_inputs(data)
    engine = get_engine()
    t0, report = time.perf_counter(), []
    with engine.begin() as conn:
        for s in (RAW, APP):
            conn.execute(text(f"DROP SCHEMA IF EXISTS {s} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {s}"))
        metadata.create_all(conn)
        for t in INPUT_TABLES:
            df = tables[t]
            pk = TABLES[t].primary_key.columns.keys()
            skip = set(exc[(exc["table_name"] == t) & exc["exception_type"].isin(UNLOADABLE)]["record_key"])
            key = df[pk].astype(str).agg("|".join, axis=1)
            keep = df[~key.isin(skip) & ~df.duplicated(pk, keep="first")]
            _copy(conn, t, keep[columns(t)])
            report.append({"table": f"{RAW}.{t}", "csv_rows": len(df), "skipped": len(df) - len(keep)})
        _copy(conn, "data_exception", exc[columns("data_exception")])
        report.append({"table": f"{APP}.data_exception", "csv_rows": len(exc), "skipped": 0})
        for stmt in foreign_keys():
            conn.execute(text(stmt))
        for r in report:
            r["db_rows"] = conn.execute(text(f"SELECT count(*) FROM {r['table']}")).scalar_one()
            r["ok"] = r["db_rows"] == r["csv_rows"] - r["skipped"]
    print(f"loaded in {time.perf_counter() - t0:.1f} s")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Load generated CSVs into PostgreSQL (idempotent)")
    ap.add_argument("--data", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    report = load(a.data)
    print(f"\n{'table':<28}{'csv rows':>10}{'skipped':>9}{'db rows':>10}  check")
    for r in report:
        print(f"{r['table']:<28}{r['csv_rows']:>10,}{r['skipped']:>9}{r['db_rows']:>10,}  {'ok' if r['ok'] else 'MISMATCH'}")
    return 0 if all(r["ok"] for r in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
