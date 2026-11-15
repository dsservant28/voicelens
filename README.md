# VoiceLens — customer feedback intelligence

**VoiceLens combines survey responses, product reviews and support messages, finds recurring themes, detects
sentiment shifts early, and turns them into prioritised action items — with every number traceable to the
records behind it.**

Customer feedback behaves like a sensor network: a problem shows up in support tickets first, then in reviews,
then in surveys. VoiceLens is built as an **early-warning system** around that idea. Because the synthetic data
comes from a simulated world with hidden incidents, we can measure not only *accuracy* but **time-to-detect**.

| | Result (full volume, held-out evaluation split) |
|---|---|
| Hidden incidents detected | **4 / 4**, **0 false alarms**, mean time-to-detect **5.25 days**, lead channel correct 4/4 |
| Sentiment accuracy | **94.1 %** (macro-F1 0.941) — **98.8 %** on the 84 % of items labelled automatically; the rest go to humans |
| Themes | micro-F1 **0.958**, exact match 94.1 % |
| Planted edge cases | **200 / 200 caught** (5 types × 40), 100 % precision, expected decision taken 200/200 |
| Data | 145,976 rows validated by 13 contract-driven checks; generated twice → byte-identical |

Full reports: [`docs/results/EVALUATION.md`](docs/results/EVALUATION.md) · [`docs/results/VALIDATION.md`](docs/results/VALIDATION.md)

---

## Architecture

```
 generate/  ──CSV/JSON/SQL──▶  validate/  ──COPY──▶  PostgreSQL  ──▶  analyze/ (9 stages)  ──▶  FastAPI  ──▶  React
 seeded world,                 13 checks from        raw.* inputs      normalize · sentiment     15+ routes     5 screens
 hidden incidents,             the data contract,    app.* outputs     themes · abstain          append-only    Why? drawer
 5 edge cases,                 quarantine path,                        aggregate · detect        events
 ground_truth/ (separate)      reproducibility                         prioritise · act
                                                                       evaluate/ (only reader of ground truth)
```

- **One data contract** (`backend/voicelens/generate/contract.py`) defines every entity once. It renders
  [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md), generates the SQL DDL and the SQLAlchemy tables, and drives the
  validator — docs, schema and checks cannot drift apart. The pipeline validates its own output with the same contract.
- **Incident-driven generator:** 4 hidden incidents (a carrier outage, a double-charge bug, a login failure, an app fix)
  *cause* the feedback, reaching support on day 0, reviews ~3 days later and surveys ~7 days later. Labels come from the
  template that produced each text, never from random assignment.
- **Explainable analysis:** multilingual lexicons (English, Spanish, Hindi, Telugu, Hinglish) with negation, contrast,
  sarcasm and hedging rules. Every prediction stores confidence, evidence tokens and the rules that fired. Uncertain items
  are **routed to human review** instead of guessed. Lexicons are written independently of the generator (policy R4).
- **Early warning:** each product × theme is tested *daily* — a 7-day window against the 28 days before it, with an exact
  Poisson tail (p ≤ 1e-5, chosen for ~11k tests) and 3-day persistence. Alert strength is shown as a magnitude
  **M = −log₁₀ p**. Per-channel tests give the lead channel.
- **Priorities and actions:** `priority = volume × negative share × severity × (1 + shift)`, stored with its inputs.
  Action items get an owner role and a recommended next step; status changes follow the contract's lifecycle and are
  append-only events.
- **Guard rails:** `scripts/policy_check.py` (also a test and an editor hook) fails the build if analysis code touches
  ground truth (R1), the generator uses unseeded randomness (R2), secrets appear in code (R3), or analysis imports the
  generator's phrase banks (R4).

Design decisions with options and trade-offs: [`docs/DECISIONS.md`](docs/DECISIONS.md) · pipeline details:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The app (5 screens)

| Screen | What it shows |
|---|---|
| **Pulse** | A three-channel *seismograph* of daily negative feedback with alert *epicenters*; the *wavefront* of the selected alert (how the signal reached support → reviews → surveys); click any point of a trace to see the exact records behind it (count reconciled). |
| **Priorities** | *Iso-priority map* — because priority = x × y, lines of equal priority are hyperbolas; ranked themes with factor bars; the action board drawn as the contract's state machine (only legal moves offered, history kept). |
| **Review** | A blind review set of 100 held-out items (the model's answer is hidden) and the uncertain queue laid out on the classifier's own decision plane (positive × negative cue weight). |
| **Data flow** | A Sankey of every loaded row (source → ingest gate → use → routing) with reconciliation checks; the 13 checks; exceptions by type; reproducibility; file integrity; the export manifest. |
| **Proof** | Evaluation: accuracy-vs-coverage frontier with a τ slider, confusion matrix, failure slices by style/language, incident time-to-detect, edge-case scoreboard, and a live checklist of every requirement. |

Everywhere: press **`/`** and paste any ID (`REV-…`, `RESP-…`, `MSG-…`, `ALR-…`, `ACT-…`, `CELL-…`) to open the
**Why?** drawer — the lineage from a number down to the redacted source text, with the classifier's evidence highlighted.
An **acting as** selector records which actor (analyst, support agent, marketing/sales ops, …, admin) made each change.

## Quickstart (fresh clone)

Prerequisites: **Python 3.13**, **Node.js 20+**, **PostgreSQL 16+** (developed on 18). Commands shown for Windows
PowerShell; on macOS/Linux use `.venv/bin/python` and `/` paths.

```powershell
git clone <repo-url> voicelens; cd voicelens
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt

# database + connection string (never committed; .env is git-ignored)
psql -U postgres -c "CREATE DATABASE voicelens;"
copy .env.example .env      # then set DATABASE_URL=postgresql://<user>:<password>@localhost:5432/voicelens

# everything in one command: generate -> validate (+ reproducibility) -> load -> analyse -> evaluate
cd backend
..\.venv\Scripts\python -m voicelens.pipeline --scale 1.0      # full volume, ~3-4 min  (--scale 0.25 for ~40 s)

# API  (http://localhost:8000/docs)
..\.venv\Scripts\python -m uvicorn voicelens.api.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

Checks (from the repo root): `.\.venv\Scripts\python -m pytest -q` (66 tests; the API tests skip automatically when
PostgreSQL is not available) and `.\.venv\Scripts\python scripts\policy_check.py`.

Individual stages, if you want them: `python -m voicelens.generate --scale 0.05`, `python -m voicelens.validate`,
`python -m voicelens.db.load`, `python -m voicelens.analyze --tau 0.6`, `python -m voicelens.evaluate`
(all from `backend/`).

> Note: the pipeline drops and reloads the database, which also clears human review and action-item history. Review in
> the UI *after* the last pipeline run; the **Recompute metrics** button only re-runs evaluation and keeps history.

## Data

- Generator: `python -m voicelens.generate --scale 1.0 --seed 20261022` → `data/output/` (git-ignored, reproducible).
  Scale 1.0 = 30,000 reviews + 20,000 survey responses + 20,000 support messages + master and event tables.
- Committed sample: [`data/sample/`](data/sample/) (scale 0.02 — CSV, JSON, `seed.sql`, ground truth, manifest,
  validation summary).
- IDs exactly as specified: `SUR-2026-000001`, `RESP-SUR-2026-000001-001`, `REV-2026-000001`,
  `MSG-TKT-2026-000001-001`, `THEME-000001` (zero-padded, immutable, identical across files).
- All text is synthetic (fictional products, `example.com` emails, `555-01xx` phones). No external data is used.

## Requirements → evidence

| Requirement (problem statement) | Where |
|---|---|
| Combine surveys, reviews, support text; themes; sentiment shifts; service priorities | Pulse, Priorities |
| Expose key decisions and exceptions; preserve traceability; measurable outputs | Why? drawer, Data flow, Proof |
| Master data first, valid parent IDs, exact ID formats | validator (`FK_MISSING`, `ID_FORMAT` = 0 except planted) |
| Taxonomies, balanced labels, neutral/mixed/sarcastic/ambiguous/multilingual text | generator, `DATA_DICTIONARY.md`, Proof slices |
| State changes as events, history not overwritten | `ticket_status_event`, `action_item_event`, `label_review_event` |
| Labels and outcomes from documented rules | template-decided gold labels (DECISIONS D-005) |
| Step 1 data dictionary (types, required, enums, units, uniqueness, rules, PK/FK, cardinality, lifecycles) | `docs/DATA_DICTIONARY.md` |
| Steps 2-4 parents first, deterministic IDs, 50k reviews/responses + 20k messages, seed + scale | generator, Data flow |
| Step 5 five labelled edge cases | `ground_truth/anomalies.csv`; Proof scoreboard (200/200) |
| Step 6 derived values computed, not generated | `DERIVED_MISMATCH` = 0 |
| Step 7 separate ground truth, never in model input | `ground_truth/`, policy R1/R4, leakage guard |
| Step 8 validation (PK, FK, enums, dates, reconciliation, lifecycle, duplicates) | `validate/`, Data flow |
| Step 9 CSV/JSON/SQL exports, README, dictionary, command, seed, manifest, validation summary | `data/sample/`, this README |
| Step 10 regenerate twice, compare checksums | validator reproducibility check (byte-identical) |
| Acceptance: human-reviewed evaluation labels | Review → blind evaluation set; Proof → model vs human |
| Acceptance: metrics measurable, privacy-safe text, trends traceable | Proof; PII redaction (`[EMAIL]` / `[PHONE]` / `[NAME]`); Pulse click-through |

## Honest limitations

- Template-generated text is cleaner than real feedback, so accuracy is optimistic; the failure slices show where the
  rules are weakest (ambiguous 75 %, negation 72 % on the eval split). Small slices (Hindi, sarcasm) have wide error bars.
- Hindi and Telugu phrase banks were not reviewed by native speakers.
- No authentication or multi-user conflict handling — the app is meant to run locally.
- The first possible alert date is 35 days into the data (the window needs a 28-day baseline).

## AI assistance

This project was built for an individual hackathon with **Claude Code** (Anthropic) as a pair programmer, as permitted
and disclosed. The owner set the goals and constraints, chose between the proposed designs, reviewed and tested every
step locally, and made all commits. Claude drafted code, tests and documentation under project rules in
[`CLAUDE.md`](CLAUDE.md) (no ground-truth leakage, deterministic generation, no secrets, no commits by the assistant)
that are enforced automatically by `scripts/policy_check.py`.
