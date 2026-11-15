"""Write outputs: csv/ + json/ (input tables), sql/seed.sql (DDL from the contract + INSERTs),
ground_truth/ (evaluation only), manifest.json (rows + SHA-256 per file). Rows sorted by PK, fixed
formats, '\\n' line endings -> byte-identical files for the same seed and scale.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from .contract import ENTITIES, INPUT_TABLES, SQL_TYPES, columns

GT_FILES = {"labels": "gt_labels", "incidents": "gt_incidents", "anomalies": "gt_anomalies"}
INSERT_BATCH = 500


def _ordered(df: pd.DataFrame, entity: str) -> pd.DataFrame:
    cols = columns(entity)
    if list(df.columns) != cols:
        raise ValueError(f"{entity}: columns {list(df.columns)} do not match the contract {cols}")
    return df.sort_values(ENTITIES[entity]["pk"], kind="mergesort").reset_index(drop=True)


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _sql(tables: dict[str, pd.DataFrame]) -> str:
    out = ["-- VoiceLens seed data (generated; do not edit). Load: psql -d voicelens -f seed.sql",
           "-- DDL is generated from backend/voicelens/generate/contract.py.",
           "-- Foreign keys are added NOT VALID after loading: planted anomalies (e.g. THEME_OUTSIDE_TAXONOMY)",
           "-- load and are reported by the validator via data_exception instead of aborting the load.",
           "BEGIN;"]
    out += [f"DROP TABLE IF EXISTS {t} CASCADE;" for t in reversed(INPUT_TABLES)]
    fks = []
    for t in INPUT_TABLES:
        e, cols = ENTITIES[t], []
        for x in e["fields"]:
            col = f"  {x['name']} {SQL_TYPES[x['type']]}" + (" NOT NULL" if x["required"] else "")
            if x["unique"] and e["pk"] != [x["name"]]:
                col += " UNIQUE"
            if x["type"] == "enum" and x["allowed"]:
                vals = ", ".join(_sql_value(a) for a in x["allowed"])
                col += f" CHECK ({x['name']} IN ({vals}))"
            cols.append(col)
            if x["fk"]:
                pt, pc = x["fk"].split(".")
                fks.append(f"ALTER TABLE {t} ADD CONSTRAINT fk_{t}_{x['name']} FOREIGN KEY ({x['name']}) "
                           f"REFERENCES {pt} ({pc}) NOT VALID;")
        cols.append(f"  PRIMARY KEY ({', '.join(e['pk'])})")
        out += [f"CREATE TABLE {t} (", ",\n".join(cols), ");"]
    for t in INPUT_TABLES:
        recs, cols = _records(tables[t]), columns(t)
        for i in range(0, len(recs), INSERT_BATCH):
            rows = ",\n".join("(" + ", ".join(_sql_value(r[c]) for c in cols) + ")" for r in recs[i:i + INSERT_BATCH])
            out.append(f"INSERT INTO {t} ({', '.join(cols)}) VALUES\n{rows};")
    out += fks + ["COMMIT;"]
    return "\n".join(out) + "\n"


def export(tables: dict[str, pd.DataFrame], gt: dict[str, pd.DataFrame], out_dir: Path, meta: dict) -> dict:
    out_dir = Path(out_dir)
    files: list[tuple[str, int]] = []
    ordered = {t: _ordered(tables[t], t) for t in INPUT_TABLES}
    for t, df in ordered.items():
        _write(out_dir / "csv" / f"{t}.csv", df.to_csv(index=False, lineterminator="\n"))
        _write(out_dir / "json" / f"{t}.json", json.dumps(_records(df), ensure_ascii=False, indent=1))
        files += [(f"csv/{t}.csv", len(df)), (f"json/{t}.json", len(df))]
    _write(out_dir / "sql" / "seed.sql", _sql(ordered))
    files.append(("sql/seed.sql", sum(len(d) for d in ordered.values())))
    for name, entity in GT_FILES.items():
        df = _ordered(gt[name], entity)
        _write(out_dir / "ground_truth" / f"{name}.csv", df.to_csv(index=False, lineterminator="\n"))
        _write(out_dir / "ground_truth" / f"{name}.json", json.dumps(_records(df), ensure_ascii=False, indent=1))
        files += [(f"ground_truth/{name}.csv", len(df)), (f"ground_truth/{name}.json", len(df))]
    manifest = dict(meta)
    manifest["files"] = [{"path": p, "rows": n, "sha256": hashlib.sha256((out_dir / p).read_bytes()).hexdigest()}
                         for p, n in files]
    _write(out_dir / "manifest.json", json.dumps(manifest, indent=2))
    return manifest
