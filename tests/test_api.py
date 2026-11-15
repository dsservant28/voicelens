"""API against the local PostgreSQL (skipped when the DB is unreachable or the pipeline has not run).
Write tests use actor/reviewer 'pytest' and remove their rows afterwards, so demo data stays clean."""
import pytest
from fastapi.testclient import TestClient

from voicelens.api import db
from voicelens.api.main import app

try:
    LOADED = bool(db.scalar("SELECT count(*) FROM app.prediction"))
except Exception:                                    # no .env / no Postgres / no tables
    LOADED = False
pytestmark = pytest.mark.skipif(not LOADED, reason="PostgreSQL with pipeline output not available")

client = TestClient(app)


def test_health_meta_overview():
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["data_loaded"]
    m = client.get("/meta").json()
    assert len(m["products"]) == 12 and len(m["themes"]) == 12 and m["run"]["run_id"].startswith("RUN-")
    o = client.get("/overview").json()
    assert o["kpis"]["items"] > 0 and o["trend"] and o["top_alerts"]


def test_alert_detail_has_series_evidence_and_lineage():
    alerts = client.get("/alerts").json()
    worsen = [a for a in alerts if a["direction"] == "worsen"]
    assert worsen
    d = client.get(f"/alerts/{worsen[0]['alert_id']}").json()
    assert d["daily_series"] and d["evidence"] and {"redacted_text", "rules_fired"} <= set(d["evidence"][0])
    act = client.get("/action-items").json()[0]
    lin = client.get(f"/lineage/action/{act['action_item_id']}").json()
    assert [c["level"] for c in lin["chain"]][:2] == ["action_item", "alert"] and lin["items"]
    assert client.get("/lineage/bogus/x").status_code == 400


def test_feedback_is_redacted():
    pii = db.one("SELECT source_type, source_id FROM app.data_exception WHERE exception_type = 'PII_LEAK' LIMIT 1")
    r = client.get(f"/feedback/{pii['source_type']}/{pii['source_id']}").json()
    assert "@" not in r["item"]["redacted_text"] and "[EMAIL]" in r["item"]["redacted_text"]
    assert any(e["exception_type"] == "PII_LEAK" for e in r["exceptions"])


def test_review_appends_event_and_leaves_queue():
    q = client.get("/review-queue?limit=1").json()
    assert q["total"] > 0 and q["reasons"]
    it = q["items"][0]
    try:
        r = client.post(f"/review/{it['source_type']}/{it['source_id']}", json={"sentiment": "negative", "reviewer": "pytest"})
        assert r.status_code == 201 and r.json()["decision"] in ("confirmed", "overridden")
        assert client.get(f"/review-queue?status=reviewed&limit=200").json()["total"] >= 1
        assert client.post(f"/review/{it['source_type']}/{it['source_id']}",
                           json={"sentiment": "joy", "reviewer": "pytest"}).status_code == 422
    finally:
        db.execute([("DELETE FROM app.label_review_event WHERE reviewer = 'pytest'", {})])


def test_action_status_lifecycle_enforced_and_logged():
    act = client.get("/action-items?status=OPEN").json()
    if not act:
        pytest.skip("no OPEN action item")
    aid = act[0]["action_item_id"]
    try:
        bad = client.post(f"/action-items/{aid}/status", json={"to_status": "DONE", "actor": "pytest"})
        assert bad.status_code == 409                                    # OPEN -> DONE is not allowed
        ok = client.post(f"/action-items/{aid}/status", json={"to_status": "IN_PROGRESS", "actor": "pytest"})
        assert ok.status_code == 201 and ok.json()["action_item"]["status"] == "IN_PROGRESS"
        assert ok.json()["events"][-1]["from_status"] == "OPEN" and "DONE" in ok.json()["allowed_next"]
    finally:
        db.execute([("DELETE FROM app.action_item_event WHERE actor = 'pytest'", {}),
                    ("UPDATE app.action_item SET status = 'OPEN' WHERE action_item_id = :i", {"i": aid})])


def test_quality_and_evaluation():
    q = client.get("/data-quality").json()
    assert q["summary"]["status"] and q["by_type"] and q["exceptions"]
    ev = client.get("/evaluation").json()
    assert ev["incidents"]["detected"] >= 1 and "eval" in ev["splits"]


def test_themes_ranked_with_priority_and_drilldown():
    t = client.get("/themes").json()
    assert t and t[0]["rank"] == 1 and all(t[i]["priority"] >= t[i + 1]["priority"] for i in range(len(t) - 1))
    d = client.get(f"/themes/{t[0]['product_id']}/{t[0]['theme_id']}").json()
    cell = d["weekly_cells"][0]
    lin = client.get(f"/lineage/cell/{cell['cell_id']}").json()
    assert len(lin["items"]) == cell["n_items"]                         # cell count reconciles with its records


def test_trend_point_traces_to_records():
    point = client.get("/overview").json()["trend"][0]
    r = client.get(f"/trend/items?week_start={point['week_start']}&channel_type={point['channel_type']}&limit=200").json()
    assert r["total"] == point["n"] and r["items"]


def test_eval_review_set_is_blind():
    q = client.get("/review-queue?set=eval&status=all&limit=200").json()
    assert q["blind"] and q["total"] == 100
    assert not ({"sentiment", "confidence", "rules_fired", "evidence"} & set(q["items"][0]))
