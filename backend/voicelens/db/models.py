"""SQLAlchemy tables GENERATED from the data contract (generate/contract.py), so the DB schema, the docs and the
validator share one definition. Schemas:  raw = input tables as loaded   app = pipeline-owned tables
(data_exception, action_item(+event), label_review_event). Ground truth is never loaded into the DB.

Foreign keys are not declared on the Table objects; db/load.py adds them after COPY as NOT VALID, so quarantined
rows (e.g. a planted THEME-000999 link) load, stay auditable, and are excluded downstream via data_exception."""
from __future__ import annotations

from sqlalchemy import (CheckConstraint, Column, Date, DateTime, Integer, MetaData, Numeric, PrimaryKeyConstraint,
                        Table, Text)

from ..generate.contract import ENTITIES, INPUT_TABLES

RAW, APP = "raw", "app"
APP_TABLES = [k for k, e in ENTITIES.items() if e["group"] == "downstream"]
SA_TYPES = {"id": Text, "str": Text, "text": Text, "enum": Text, "int": Integer, "float": Numeric,
            "date": Date, "datetime": DateTime}

metadata = MetaData()


def schema_of(table: str) -> str:
    return RAW if table in INPUT_TABLES else APP


def _table(name: str) -> Table:
    e, cols, cons = ENTITIES[name], [], []
    for x in e["fields"]:
        cols.append(Column(x["name"], SA_TYPES[x["type"]](), nullable=not x["required"],
                           unique=x["unique"] and e["pk"] != [x["name"]], comment=x["rule"] or None))
        if x["type"] == "enum" and x["allowed"]:
            vals = ", ".join(str(a) if isinstance(a, int) else "'" + a + "'" for a in x["allowed"])
            cons.append(CheckConstraint(f"{x['name']} IN ({vals})", name=f"ck_{name}_{x['name']}"))
    return Table(name, metadata, *cols, PrimaryKeyConstraint(*e["pk"], name=f"pk_{name}"), *cons,
                 schema=schema_of(name), comment=e["description"])


TABLES: dict[str, Table] = {t: _table(t) for t in INPUT_TABLES + APP_TABLES}


def foreign_keys() -> list[str]:
    """ALTER statements for every contract FK, added NOT VALID (existing rows not re-checked)."""
    out = []
    for t, tbl in TABLES.items():
        for x in ENTITIES[t]["fields"]:
            if x["fk"]:
                pt, pc = x["fk"].split(".")
                out.append(f"ALTER TABLE {schema_of(t)}.{t} ADD CONSTRAINT fk_{t}_{x['name']} FOREIGN KEY ({x['name']}) "
                           f"REFERENCES {schema_of(pt)}.{pt} ({pc}) NOT VALID")
    return out
