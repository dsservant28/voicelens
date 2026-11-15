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
