"""Generator tests (scale 0.02 for speed): reproducibility, IDs, joins, balance, coverage, dates, incidents,
edge cases, and separation of ground truth from input files."""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from voicelens.generate import contract
from voicelens.generate.__main__ import generate
from voicelens.generate.taxonomy import OUT_OF_TAXONOMY_THEME_ID

SCALE = 0.02
LEAK_TERMS = re.compile(r"(ground_truth|issue_type|true_sentiment|true_theme|gold_label|human_label|incident|template_id|split)")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("gen_a")
    tables, gt, manifest = generate(SCALE, 20261022, out)
    return out, tables, gt, manifest


def _csv(out: Path, table: str) -> pd.DataFrame:
    return pd.read_csv(out / "csv" / f"{table}.csv", dtype=str, keep_default_na=False)


def test_same_seed_same_checksums_and_different_seed_differs(run, tmp_path):
    _, _, _, m1 = run
    m2 = generate(SCALE, 20261022, tmp_path / "b")[2]
    m3 = generate(SCALE, 7, tmp_path / "c")[2]
    sums = lambda m: {f["path"]: (f["rows"], f["sha256"]) for f in m["files"]}
    assert sums(m1) == sums(m2)
    assert sums(m1) != sums(m3)


def test_files_match_contract_and_ids_match_patterns(run):
    out = run[0]
    for t in contract.INPUT_TABLES:
        df = _csv(out, t)
        assert list(df.columns) == contract.columns(t), t
        pk = contract.ENTITIES[t]["pk"]
        assert not df.duplicated(pk).any(), f"duplicate PK in {t}"
        for col, pat in contract.ID_PATTERNS.items():
            if col in df.columns and col in pk:
                bad = df[~df[col].str.match(pat)]
                assert bad.empty, f"{t}.{col}: {bad[col].head().tolist()}"


def test_child_ids_embed_parent_ids(run):
    out = run[0]
    r = _csv(out, "survey_response")
    assert (r["response_id"].str.slice(5, 20) == r["survey_id"]).all()          # RESP-SUR-2026-000001-001
    m = _csv(out, "support_message")
    assert (m["message_id"].str.slice(4, 19) == m["ticket_id"]).all()           # MSG-TKT-2026-000001-001


def test_foreign_keys_resolve_except_planted(run):
    out = run[0]
    tables = {t: _csv(out, t) for t in contract.INPUT_TABLES}
    for t in contract.INPUT_TABLES:
        for x in contract.ENTITIES[t]["fields"]:
            if not x["fk"]:
                continue
            pt, pc = x["fk"].split(".")
            vals = tables[t][x["name"]]
            vals = vals[vals != ""]
            missing = set(vals) - set(tables[pt][pc])
            if t == "feedback_theme":
                missing -= {OUT_OF_TAXONOMY_THEME_ID}
            assert not missing, f"{t}.{x['name']} -> {pt}: {sorted(missing)[:3]}"
    # polymorphic source ids
    ids = set(tables["review"]["review_id"]) | set(tables["survey_response"]["response_id"]) | set(
        tables["support_message"]["message_id"])
    for t in ("sentiment_label", "feedback_theme"):
        assert set(tables[t]["source_id"]) <= ids


def test_enums_and_required(run):
    out = run[0]
    for t in contract.INPUT_TABLES:
        df = _csv(out, t)
        for x in contract.ENTITIES[t]["fields"]:
            col = df[x["name"]]
            if x["required"]:
                assert (col != "").all(), f"{t}.{x['name']} has blanks"
            if x["allowed"]:
                allowed = {str(a) for a in x["allowed"]} | ({""} if not x["required"] else set())
                assert set(col) <= allowed, f"{t}.{x['name']}: {set(col) - allowed}"


def test_balance_and_coverage(run):
    labels = run[2]["labels"]
    base = labels[labels["incident_id"].isna()]
    share = base["sentiment"].value_counts(normalize=True)
    assert all(abs(share[s] - 0.25) < 0.03 for s in contract.SENT), share.to_dict()
    assert set(labels["style"]) == set(contract.STYLES)
    assert set(labels["language"]) == set(contract.LANG)
    themes = set("|".join(labels["theme_ids"]).split("|"))
    assert len(themes) == 12


def test_dates_and_lifecycle(run):
    out = run[0]
    s = _csv(out, "survey").set_index("survey_id")
    r = _csv(out, "survey_response")
    d = r["submitted_at"].str.slice(0, 10)
    assert (d >= r["survey_id"].map(s["opens_at"])).all() and (d <= r["survey_id"].map(s["closes_at"])).all()
    t = _csv(out, "support_ticket").set_index("ticket_id")
    m = _csv(out, "support_message")
    assert (m["sent_at"] >= m["ticket_id"].map(t["opened_at"])).all()
    closed = m["ticket_id"].map(t["closed_at"])
    assert ((closed == "") | (m["sent_at"] <= closed)).all()
    e = _csv(out, "ticket_status_event")
    legal = {("", "OPEN"), ("OPEN", "IN_PROGRESS"), ("IN_PROGRESS", "RESOLVED"), ("RESOLVED", "CLOSED"),
             ("RESOLVED", "REOPENED"), ("REOPENED", "IN_PROGRESS")}
    assert set(zip(e["from_status"], e["to_status"])) <= legal
    last = e.sort_values(["ticket_id", "event_at"]).groupby("ticket_id")["to_status"].last()
    assert (t["current_status"] == last.reindex(t.index)).all()     # status is derived from events


def test_incidents_bend_negative_share(run):
    labels, inc = run[2]["labels"], run[2]["incidents"]
    assert len(inc) == 4 and (inc["lag_support_days"] == 0).all()
    assert (inc["lag_review_days"] == 3).all() and (inc["lag_survey_days"] == 7).all()
    for _, i in inc[inc["direction"] == "worsen"].iterrows():
        caused = labels[(labels["incident_id"] == i["incident_id"]) & (labels["incident_phase"] == "post")]
        assert len(caused) > 0 and (caused["sentiment"] == "negative").all()
        assert (caused["theme_ids"] == i["theme_id"]).all()


def test_edge_cases_planted_and_traceable(run):
    out, tables, gt, _ = run
    a = gt["anomalies"]
    assert set(a["issue_type"]) == set(contract.ISSUE_TYPES)
    assert (a["issue_type"].value_counts() >= 3).all()
    pk = {"review": "review_id", "survey_response": "response_id", "support_message": "message_id"}
    for _, row in a.iterrows():
        assert row["source_id"] in set(_csv(out, row["source_type"])[pk[row["source_type"]]])
    leaked = a[a["issue_type"] == "TEST_LABEL_IN_MODEL_INPUT"]
    rev_resp = pd.concat([_csv(out, "review").rename(columns={"review_id": "id"}),
                          _csv(out, "survey_response").rename(columns={"response_id": "id"})])
    assert rev_resp[rev_resp["id"].isin(leaked["source_id"])]["tags"].str.contains("eval_label=").all()


def test_ground_truth_separate_from_inputs(run):
    out = run[0]
    for t in contract.INPUT_TABLES:
        cols = _csv(out, t).columns
        assert not [c for c in cols if LEAK_TERMS.search(c)], t
    gt_files = {p.name for p in (out / "ground_truth").iterdir()}
    assert gt_files == {"labels.csv", "labels.json", "incidents.csv", "incidents.json",
                        "anomalies.csv", "anomalies.json"}
    for sub in ("csv", "json", "sql"):
        assert not any("labels" == p.stem or "anomal" in p.stem for p in (out / sub).iterdir())
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["seed"] == 20261022 and len(manifest["files"]) == 31
