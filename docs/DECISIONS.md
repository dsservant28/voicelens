# Design decisions and assumptions

Owner-written. One entry per decision. Format: Decision · Options considered · Choice and why · Trade-off · Requirement link.

---

## D-001 — Architecture: 3-tier (React → FastAPI → PostgreSQL)
- **Options considered:** Streamlit single app; FastAPI + React + PostgreSQL.
- **Choice and why:** _(write in your own words)_
- **Trade-off:**
- **Requirement link:** end-to-end workflow, multiple actors, traceability.

## D-002 — Explainable rule/lexicon analysis instead of a trained ML model
- **Options considered:** lexicon + rules; scikit-learn classifier; LLM API.
- **Choice and why:** _(write in your own words)_
- **Trade-off:**
- **Requirement link:** expose key decisions, measurable metrics, privacy-safe, 6-hour limit.

> D-003…D-006 drafted by Claude from the approved Step 1 plan. Owner: rewrite "Choice and why" in your own words.

## D-003 — One data contract drives docs, DDL and validation
- **Decision:** `generate/contract.py` defines every entity once (types, required, enums, units, uniqueness, FKs, cardinality, effective dates, lifecycle).
- **Options considered:** hand-written markdown dictionary + separate checks; one machine-readable contract.
- **Choice and why:** DATA_DICTIONARY.md and the seed.sql DDL are generated from the contract, and the validator will read it too, so the docs and the checks cannot drift apart.
- **Trade-off:** markdown formatting is fixed by the renderer; changing the schema means changing Python.
- **Requirement link:** Step 1 data dictionary, Step 8 validation, Step 9 schema export.

## D-004 — Incident-driven synthetic world with per-channel lag
- **Decision:** 4 hidden incidents (3 worsen, 1 improve) cause the sentiment shifts. A signal shows in support on day 0, reviews +3, surveys +7 days. Stored in `ground_truth/incidents.csv`.
- **Options considered:** independent random rows with planted weekly spikes; causal incidents.
- **Choice and why:** shifts have a known cause and onset, so the detector can be scored on hit rate and time-to-detect per channel, not only on accuracy.
- **Trade-off:** at small scales (0.05) an incident causes only a handful of items per channel; detection metrics are meaningful at scale ≥ 0.25.
- **Requirement link:** sentiment shifts, measurable outputs, traceability.

## D-005 — Input tags vs gold labels; template decides the label
- **Decision:** gold labels for every item (from the template that produced it) live only in `ground_truth/labels.csv`. Input `sentiment_label`/`feedback_theme` contain source-system tags on ~30% of TRAIN items only; the eval split (2,000 at scale 1, stratified by sentiment) is never tagged in input.
- **Options considered:** random label assignment; labels in input files; template-derived gold kept separate.
- **Choice and why:** labels follow documented rules and cannot leak into analysis input.
- **Trade-off:** template text is cleaner than real text, so accuracy will be optimistic; we report slice metrics (sarcasm, negation, ambiguous, each language) to show where it fails.
- **Requirement link:** rule-based labels, no leakage, evaluation set.

## D-006 — Edge cases injected after the baseline, labelled only in ground truth
- **Decision:** max(3, round(40×scale)) records per type, on disjoint records, each listed in `ground_truth/anomalies.csv` with `expected_decision`. Foreign keys in seed.sql are added `NOT VALID`, so the planted bad theme link loads and is reported, not crashed on.
- **Options considered:** one example per type; corrupting random rows silently.
- **Choice and why:** several examples per type make per-type detection recall measurable; unrelated rows stay valid.
- **Trade-off:** NOT VALID FKs mean the DB does not stop bad rows from loading; the validator is responsible for catching them.
- **Requirement link:** required edge cases, exception path, separate ground truth.

## D-007 — Ingest gate quarantines, never crashes
- **Decision:** `validate/checks.py` runs 13 contract-driven checks; every failing row becomes an `app.data_exception` row with a disposition: QUARANTINE (kept in the DB, excluded from analysis) or FLAG (kept, shown on the data-quality page).
- **Options considered:** fail the whole load on the first error; silently drop bad rows; quarantine with an audit trail.
- **Choice and why:** _(owner)_ bad rows stay visible and traceable; one bad record never blocks thousands of good ones.
- **Trade-off:** downstream queries must anti-join quarantined keys.
- **Requirement link:** Step 8 validation, exception path, traceability.

## D-008 — Contract-generated DB schema, COPY load, FKs NOT VALID, no ground truth in DB
- **Decision:** SQLAlchemy tables are generated from the contract (`db/models.py`), schemas `raw` (inputs) and `app` (pipeline-owned). Load = drop/recreate + PostgreSQL COPY (idempotent). FKs added `NOT VALID` after load: planted bad links load and are reported, while any NEW bad insert is rejected. Ground truth stays in files, read only by `evaluate/`.
- **Options considered:** hand-written ORM classes + row INSERTs; Alembic migrations.
- **Choice and why:** _(owner)_ one definition for docs, checks and DDL; COPY loads 36k rows in ~3 s.
- **Trade-off:** no migration history (drop/recreate is fine for a generated dataset).
- **Requirement link:** Step 9 schema export, no label leakage.

## D-009 — Analysis is independent of the generator (policy R4) and tuned on train only
- **Decision:** `analyze/` may import only `generate.contract`/`generate.config`; lexicons in `analyze/lexicon.py` are hand-written. Rules were tuned by looking at TRAIN-split errors only; the eval split is reported once (Step 5). Each `pipeline_run` stores a hash of the rule files.
- **Options considered:** reuse the generator's phrase banks; tune on all data; independent lexicon + train-only tuning.
- **Choice and why:** _(owner)_ otherwise accuracy would just measure "the generator reversed itself".
- **Trade-off:** template text is still cleaner than real text; train numbers are optimistic, eval/slice metrics are the honest ones.
- **Requirement link:** no label leakage, measurable metrics, explainability.

## D-010 — Confidence + abstention instead of forced labels
- **Decision:** every prediction has confidence, evidence tokens and rule ids. Routed to human review if confidence < tau (0.6 default, chosen later from the accuracy-vs-coverage curve), sarcasm, no theme, rating-vs-text conflict, or input-label conflict. PII is redacted before analysis (PII_LEAK exception); input labels that contradict confident predictions raise LABEL_CONTRADICTS_TEXT.
- **Options considered:** always auto-label; abstain on low confidence only.
- **Choice and why:** _(owner)_ honest AI: show coverage and accuracy together; humans see the hard cases.
- **Trade-off:** ~16% of items need human review.
- **Requirement link:** human review loop, explainability, edge cases.

## D-011 — Daily rolling detection with an exact Poisson test and persistence
- **Decision:** every day, per product x theme, a 7-day window is compared with the 28 days before it. Worsen = excess negatives with exact Poisson tail p <= 1e-5 (~11k tests -> Bonferroni-style), >= 8 negatives and share +0.15; improve = share -0.30 with z >= 4. An alert is confirmed after 3 firing days and `detected_date` is that day (no hindsight). Per-channel series give the lead channel. Improve after a recent worsen = `recovery`.
- **Options considered:** weekly buckets + z-score; daily rolling + z; daily rolling + exact tail + persistence.
- **Choice and why:** _(owner)_ day-level time-to-detect; a small-count z-score fired ~190 times on noise, the exact tail + persistence fires only on real shifts. Thresholds come from the multiple-testing argument, not from the incidents.
- **Trade-off:** the 3-day confirmation adds ~2 days to time-to-detect; first possible detection is 35 days into the data.
- **Requirement link:** sentiment shifts, measurable time-to-detect, traceability (alert_evidence).

## D-012 — Priority formula stored with inputs; action items upserted
- **Decision:** priority = volume x neg_share x severity_weight x (1 + shift), inputs stored as JSON. Action item if priority >= 10 and the alert lasted >= 7 days, plus chronic issues (>= 60% negative over 28 days, >= 15 items). Upsert key (product, theme, kind): reruns refresh score/evidence; status history in `action_item_event` is never touched.
- **Options considered:** drop and recreate each run; upsert.
- **Choice and why:** _(owner)_ reruns must not erase human decisions.
- **Trade-off:** items that stop qualifying are not auto-closed (a human decides).
- **Requirement link:** prioritised action items, append-only history, traceability.

## D-013 — Evaluation: eval split once, tau chosen on train, everything reported
- **Decision:** `evaluate/` (the only package reading ground truth) reports sentiment/theme metrics on the untouched eval split next to train ("tuned on"), slices by style and language, the accuracy-vs-coverage curve, edge-case recall/precision and whether the expected decision was taken, and incident detection rate / false alarms / time-to-detect / measured vs designed channel lag / evidence precision. tau is recommended from the TRAIN curve (max coverage with auto accuracy >= target); the owner decides whether to apply it.
- **Options considered:** single accuracy number; tune tau on eval.
- **Choice and why:** _(owner)_ honest metrics: no decision is ever fitted on the eval split.
- **Trade-off:** eval split at scale 0.25 is ~500 items, so small slices (hi, sarcastic) have wide error bars.
- **Requirement link:** measurable outputs, evaluation set, edge-case handling, time-to-detect.

## D-014 — API: plain SQL per router, append-only writes, one-command pipeline for a fresh clone
- **Decision:** FastAPI routers (overview, alerts/lineage, feedback/review, action items, quality/evaluation) over parameterised SQL. POSTs only append events (`label_review_event`, `action_item_event`); action status transitions are checked against the contract's lifecycle (409 if illegal). `python -m voicelens.pipeline` runs generate -> validate -> load -> analyze -> evaluate and copies the reports to `docs/results/`. No auth: the app runs on the reviewer's own machine; nothing secret is in code.
- **Options considered:** ORM models + repositories; auth tokens.
- **Choice and why:** _(owner)_ few, readable queries; a reviewer can go from `git clone` to a running API with one command.
- **Trade-off:** no authentication or multi-user conflict handling (documented limitation).
- **Requirement link:** end-to-end workflow, human review loop, traceability, reproducibility.
