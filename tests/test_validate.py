"""Stage-1 ingest gate: zero false positives on clean generated data, 100% recall on the ingest-detectable planted
anomalies, every check fires on a deliberately corrupted copy (and nothing crashes), DDL compiles from the contract."""
import pandas as pd
import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from voicelens.db.models import TABLES, foreign_keys
from voicelens.generate.__main__ import generate
from voicelens.validate.__main__ import load_inputs, validate
from voicelens.validate.checks import CHECKS, run_checks
from voicelens.validate.reproduce import reproducibility

SCALE = 0.02
INGEST_DETECTABLE = {"DUPLICATE_RESPONSE", "THEME_OUTSIDE_TAXONOMY", "TEST_LABEL_IN_MODEL_INPUT"}
NATURAL_FLAGS = {"DUPLICATE_REVIEW"}          # genuine template collisions, flagged not quarantined


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    out = tmp_path_factory.mktemp("val")
    gt = generate(SCALE, 20261022, out)[1]
    return out, gt


def test_clean_data_only_planted_or_natural_flags(data):
    out, _ = data
    exc = run_checks(load_inputs(out))
    assert set(exc["exception_type"]) <= INGEST_DETECTABLE | NATURAL_FLAGS, exc["exception_type"].value_counts()


def test_planted_anomalies_caught(data):
    out, gt = data
    exc = run_checks(load_inputs(out))
    a = gt["anomalies"][gt["anomalies"]["issue_type"].isin(INGEST_DETECTABLE)]
    found = set(zip(exc["exception_type"], exc["source_type"], exc["source_id"]))
    missed = [r for r in a.itertuples() if (r.issue_type, r.source_type, r.source_id) not in found]
    assert not missed
    assert (exc[exc["exception_type"].isin(INGEST_DETECTABLE)]["disposition"] == "QUARANTINE").all()


def test_every_check_fires_on_corruption_without_crashing(data):
    T = load_inputs(data[0])
    T["customer"] = pd.concat([T["customer"], T["customer"].head(1)])                  # PK_DUPLICATE + UNIQUE
    T["product"].loc[0, "status"] = "ZOMBIE"                                            # ENUM_INVALID
    T["review"].loc[0, "rating"] = "five"                                               # TYPE_INVALID
    T["review"].loc[1, "customer_id"] = "CUST-999999"                                   # FK_MISSING
    T["review"].loc[2, "text"] = ""                                                     # REQUIRED_MISSING
    T["review"].loc[3, "review_id"] = "REV-26-1"                                        # ID_FORMAT
    T["review"].loc[4, "tags"] = "vip"                                                  # TAG_UNKNOWN
    T["review"] = pd.concat([T["review"], T["review"].iloc[[5]].assign(review_id="REV-2026-999999")])  # DUPLICATE_REVIEW
    T["survey"].loc[0, "closes_at"] = "2020-01-01"                                      # DATE_ORDER
    T["support_ticket"].loc[0, "current_status"] = "OPEN"                               # DERIVED_MISMATCH
    e = T["ticket_status_event"]
    e.loc[e.index[1], "to_status"] = "CLOSED"                                           # LIFECYCLE_ILLEGAL
    exc = run_checks(T)
    assert {c.name for c in CHECKS} <= set(exc["check_name"]), {c.name for c in CHECKS} - set(exc["check_name"])


def test_summary_written_and_reproducible(data, tmp_path):
    out, _ = data
    s = validate(out, repro=False)
    assert s["status"] == "PASS_WITH_EXCEPTIONS" and all(i["ok"] for i in s["file_integrity"])
    for f in ("data_exception.csv", "validation_summary.json", "validation_summary.md"):
        assert (out / "validation" / f).exists()
    r = reproducibility(20261022, 0.01)
    assert r["runs_identical"] and r["passed"]


def test_ddl_compiles_from_contract():
    for t in TABLES.values():
        ddl = str(CreateTable(t).compile(dialect=postgresql.dialect()))
        assert "PRIMARY KEY" in ddl
    assert all("NOT VALID" in s for s in foreign_keys()) and len(foreign_keys()) >= 15
