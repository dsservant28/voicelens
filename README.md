<div align="center">

# VoiceLens

**Customer feedback intelligence — an early-warning system for what customers are telling you.**<br/>
Survey responses, product reviews and support messages → recurring themes, sentiment shifts, service priorities and action items, with every number traceable to the records behind it.

**[Run it locally](#8-run-it-yourself)** &nbsp;·&nbsp; **[The app](#5-the-app)** &nbsp;·&nbsp; **[Results](#4-results)** &nbsp;·&nbsp; **[Key decisions](#7-key-decisions)**

<br/>

<img src="docs/images/pulse.png" alt="Pulse: three-channel seismograph with alert epicenters and the wavefront of the selected alert" width="900">

<sub>Pulse — three channels on one timeline. Each epicenter is a statistically confirmed shift; the wavefront shows the signal reaching support first, then reviews, then surveys.</sub>

</div>

---

## Contents

1. [The problem](#1-the-problem)
2. [What we built](#2-what-we-built)
3. [How it works](#3-how-it-works)
4. [Results](#4-results)
5. [The app](#5-the-app)
6. [The data](#6-the-data)
7. [Key decisions](#7-key-decisions)
8. [Run it yourself](#8-run-it-yourself)
9. [Reference](#9-reference)

---

## 1. The problem

Companies hear from customers through three channels — surveys, reviews and support — but read them separately. The
brief: **combine them, find recurring themes, detect sentiment shifts and turn them into service priorities**, while
exposing every decision and exception, preserving traceability and producing measurable results.

Our framing: feedback behaves like a **sensor network**. When something breaks, support tickets react first, reviews a
few days later, surveys last. So VoiceLens is built as an **early-warning system**: it should catch the problem early,
say how sure it is, hand the uncertain cases to a human, and prove every number.

---

## 2. What we built

```mermaid
flowchart LR
    G["Generator<br/>seeded world, hidden incidents,<br/>5 planted edge cases"] -->|CSV · JSON · SQL| V["Ingest gate<br/>13 contract checks,<br/>quarantine, reproducibility"]
    V -->|COPY| DB[("PostgreSQL<br/>raw · app")]
    DB --> A["Analysis pipeline<br/>normalize → sentiment & themes → abstain<br/>→ aggregate → detect → prioritise → act"]
    A --> DB
    DB --> API["FastAPI<br/>REST + append-only events"]
    API --> UI["React app<br/>5 screens + Why? drawer"]
    GT[/"ground_truth/<br/>labels · incidents · anomalies"/] --> E["Evaluation"]
    DB --> E
    E --> UI
```

| Layer | Folder | What it does |
|---|---|---|
| Data contract | `backend/voicelens/generate/contract.py` | Defines every entity once; renders the data dictionary, the SQL DDL and the DB tables, and drives the validator |
| Generator | `backend/voicelens/generate/` | Deterministic synthetic world (seed `20261022`, `--scale`), labels decided by templates, ground truth kept separate |
| Validation | `backend/voicelens/validate/` | PK, FK, enums, types, IDs, dates, derived values, lifecycles, duplicates, leakage → `data_exception`; generate-twice reproducibility |
| Database | `backend/voicelens/db/` | Tables generated from the contract, bulk `COPY` load, foreign keys `NOT VALID` so planted anomalies load and get reported |
| Analysis | `backend/voicelens/analyze/` | 8 explainable stages (below); never reads ground truth |
| Evaluation | `backend/voicelens/evaluate/` | The only code that reads ground truth: accuracy, slices, coverage curve, edge-case recall, time-to-detect |
| API | `backend/voicelens/api/` | FastAPI, one router per area, interactive docs at `/docs` |
| App | `frontend/` | React + TypeScript + Tailwind + d3 + motion |

---

## 3. How it works

```mermaid
flowchart TD
    R["raw feedback<br/>(reviews · survey responses · customer support messages)"] --> N["1 · Normalize<br/>PII redaction · language detection · quarantined rows excluded"]
    N --> S["2 · Sentiment<br/>multilingual lexicons + negation, contrast, sarcasm, hedging rules<br/>→ label, confidence, evidence, rules fired"]
    N --> T["3 · Themes<br/>taxonomy keywords · product names masked · child beats parent"]
    S --> AB{"4 · Abstain<br/>confidence < τ, sarcasm, no theme,<br/>rating or label conflict?"}
    T --> AB
    AB -->|no| AUTO["auto-labelled"]
    AB -->|yes| HUM["human review queue"]
    AUTO --> AG["5 · Aggregate<br/>product × theme × channel × week, with member lists"]
    HUM --> AG
    AG --> D["6 · Detect<br/>daily: 7-day window vs 28-day baseline,<br/>exact Poisson p ≤ 1e-5, 3-day persistence"]
    D --> P["7 · Prioritise<br/>priority = volume × neg share × severity × (1 + shift)"]
    P --> ACT["8 · Act<br/>action item + owner + recommendation, append-only history"]
```

- **Explainable by construction.** Every prediction stores its confidence, the evidence tokens it matched and the rules
  that fired. The app highlights those tokens in the text: green for positive cues, red for negative, strikethrough for
  negated, wavy underline for sarcasm.
- **Honest about uncertainty.** Items below the confidence threshold τ (0.6), or with sarcasm, no theme, or a conflict
  between rating and text, go to a human instead of being guessed.
- **Alert strength as a magnitude.** Every alert has **M = −log₁₀ p**, like the Richter scale. M ≥ 5 is the detection gate.
- **Lead channel.** Each channel is also tested on its own series, so every alert records which channel moved first.
- **Guard rails.** `scripts/policy_check.py` runs as a test and as an editor hook and fails if analysis code reads ground
  truth, the generator uses unseeded randomness, a secret appears in code, or analysis imports the generator's phrase
  banks.

---

## 4. Results

Full volume (scale 1.0), measured on the **held-out evaluation split** — rules were tuned on the training split only.

| Measure | Result |
|---|---:|
| Hidden incidents detected | **4 / 4** |
| False alarms | **0** |
| Mean time-to-detect | **5.25 days** after onset |
| Lead channel correct | **4 / 4** (support first) |
| Sentiment accuracy · macro-F1 | **94.2 %** · 0.942 |
| Accuracy on auto-labelled items | **98.5 %** at 83.5 % coverage |
| Themes micro-F1 · exact match | **0.951** · 93.1 % |
| Planted edge cases caught | **200 / 200** (5 types × 40), 100 % precision, expected decision taken 200/200 |
| Rows validated · reproducible | **147,488** rows, 13 checks · generated twice → byte-identical |

<details>
<summary><b>Edge cases — planted vs caught</b></summary>
<br/>

| Edge case | Caught | Expected decision | How |
|---|---:|---|---|
| Label contradicts text | 40/40 | flag for human review | input label disagrees with a confident prediction → review queue |
| Duplicate response | 40/40 | drop duplicate, keep first | same customer + survey → quarantined |
| Customer identity leaked | 40/40 | redact before analysis | email / phone / known name → `[EMAIL]` `[PHONE]` `[NAME]` |
| Theme outside taxonomy | 40/40 | reject link, log exception | foreign key to the theme table fails → quarantined |
| Test label in model input | 40/40 | strip and exclude | label-like value in `tags` → quarantined; `tags` is never a feature |

</details>

Full reports: [`docs/results/EVALUATION.md`](docs/results/EVALUATION.md) · [`docs/results/VALIDATION.md`](docs/results/VALIDATION.md)

---

## 5. The app

Five screens. Everywhere, press **`/`** and paste any ID (`REV-…`, `RESP-…`, `MSG-…`, `ALR-…`, `ACT-…`, `CELL-…`) to
open the **Why?** drawer, and use **acting as** to choose the actor (analyst, support agent, marketing / sales ops,
billing, logistics, product manager, admin) recorded on every change.

### Pulse — signals, alerts and epicenters

Three channel traces share one timeline; epicenters mark confirmed shifts with their magnitude. Click an epicenter to see
its wavefront, statistics, linked action and evidence. Click any point of a trace to see the exact records behind that
value — the count is reconciled on screen. *(Screenshot at the top.)*

### Priorities — themes and action items

Because priority = x × y on this chart, the dashed hyperbolas are **lines of equal priority**. Below: ranked themes with
factor bars, the selected theme's weekly history, and the action board drawn as the contract's state machine — only legal
moves are offered, and every move is kept as history.

<img src="docs/images/priorities.png" alt="Priorities: iso-priority map, ranked factor table and action board" width="900">

### Review — humans decide where the rules are unsure

The uncertain queue laid out on the classifier's own decision plane (positive × negative cue weight), plus a blind
evaluation set of 100 held-out items where the model's answer is hidden from the reviewer.

<img src="docs/images/review.png" alt="Review: sentiment decision plane and uncertain queue" width="900">

### Data flow — every row accounted for

A Sankey from source to ingest gate to use to routing, with three reconciliation checks; the 13 contract checks;
exceptions by type; reproducibility; file integrity; and the export manifest.

<img src="docs/images/flow.png" alt="Data flow: reconciled Sankey, checks and exceptions" width="900">

### Proof — evaluation and a live requirements checklist

Every line of the problem statement with a live status and a link to its evidence; the accuracy-vs-coverage frontier with
a τ slider; confusion matrix; failure slices; incident time-to-detect; edge-case scoreboard.

<img src="docs/images/proof.png" alt="Proof: requirements checklist, metrics, frontier, confusion matrix, slices" width="900">

<details>
<summary><b>The Why? drawer — lineage from a number to the source text</b></summary>
<br/>

An action item's priority formula with its real numbers → the alert behind it (magnitude, test, lead channel) → the
records, with the classifier's evidence highlighted and personal data redacted.

<img src="docs/images/why.png" alt="Why? drawer for an action item" width="900">

</details>

<details>
<summary><b>Action item lifecycle</b></summary>
<br/>

```mermaid
stateDiagram-v2
    [*] --> OPEN: created by rule
    OPEN --> IN_PROGRESS
    OPEN --> DISMISSED
    IN_PROGRESS --> DONE
    IN_PROGRESS --> DISMISSED
    DONE --> [*]
    DISMISSED --> [*]
```

Transitions come from the data contract; the API rejects anything else with `409`. Each move is a new
`action_item_event` row — history is never overwritten.

</details>

---

## 6. The data

All data is synthetic, generated by one seeded generator (`--seed 20261022`, `--scale`). Scale 1.0 produces
**30,000 reviews + 20,040 survey responses (50,040) and 20,424 support messages**, plus master and event tables.

```mermaid
erDiagram
    CUSTOMER ||--o{ REVIEW : writes
    CUSTOMER ||--o{ SURVEY_RESPONSE : answers
    CUSTOMER ||--o{ SUPPORT_TICKET : opens
    PRODUCT ||--o{ REVIEW : about
    PRODUCT |o--o{ SURVEY : "optional"
    CHANNEL ||--o{ REVIEW : via
    SURVEY ||--o{ SURVEY_RESPONSE : collects
    SUPPORT_TICKET ||--o{ SUPPORT_MESSAGE : contains
    SUPPORT_TICKET ||--o{ TICKET_STATUS_EVENT : history
    THEME |o--o{ THEME : parent
    THEME ||--o{ FEEDBACK_THEME : tags
    THEME ||--o{ ACTION_ITEM : drives
    ACTION_ITEM ||--o{ ACTION_ITEM_EVENT : history
```

- **Hidden incidents cause the shifts.** Four incidents (a carrier outage, a double-charge bug, a login failure and an app
  fix) change sentiment for one product and theme, reaching support on day 0, reviews about 3 days later and surveys about
  7 days later. They are stored only in `ground_truth/incidents.csv`, so detection can be scored on time-to-detect.
- **Labels follow documented rules.** Each text comes from a template that decides its sentiment and theme. Coverage
  includes neutral, mixed, sarcastic, negated, ambiguous and multilingual text (Spanish, Hindi, Telugu, Hinglish).
- **Exact IDs:** `SUR-2026-000001`, `RESP-SUR-2026-000001-001`, `REV-2026-000001`, `MSG-TKT-2026-000001-001`,
  `THEME-000001` — zero-padded, immutable, identical across files.
- **Derived values are computed,** never randomly generated: survey status, ticket status and closed date, ratings and
  scores from sentiment, counts and priorities.
- **Ground truth is separate** (`data/output/ground_truth/`) and never loaded into the database.

Field-level definitions, PK/FK, cardinality, optional relationships, effective dates and lifecycles:
[`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md). A small committed export (CSV, JSON, SQL, ground truth, manifest,
validation summary) is in [`data/sample/`](data/sample/).

---

## 7. Key decisions

The choices that shaped the project most:

| Decision | Why |
|---|---|
| One data contract for docs, schema and checks | The dictionary, the DDL and the validator cannot drift apart; the pipeline checks its own output with it |
| A simulated world with hidden incidents and channel lag | Shifts have a known cause and onset, so detection is scored on time-to-detect, not just accuracy |
| Labels from templates, ground truth in separate files | Labels follow documented rules and can never leak into analysis input |
| Quarantine bad rows instead of failing or dropping them | One bad record never blocks thousands of good ones, and every exception stays auditable |
| Explainable rules instead of a trained model | Every label shows its evidence and rules; no heavy ML or paid APIs; easy to audit |
| Lexicons written independently, tuned on the training split only | Accuracy is not "the generator reversed itself"; the evaluation split is reported once |
| Abstain below τ and route to humans | 98.5 % accuracy on what is labelled automatically; the hard cases are visible, not hidden |
| Daily rolling test, exact Poisson tail, 3-day persistence | Day-level time-to-detect; a simpler z-score fired about 190 times on noise, this fires only on real shifts |
| Priority formula stored with its inputs | Any score can be broken down factor by factor in the UI |
| Append-only events for tickets, actions and reviews | History is never overwritten; status is derived from the latest event |
| UI built on the system's own math | Magnitude, wavefront, iso-priority hyperbolas and the decision plane are real quantities, not decoration |

Every decision with the options considered and the trade-offs: [`docs/DECISIONS.md`](docs/DECISIONS.md).

---

## 8. Run it yourself

**You need three things installed** (check each with the command in brackets):

1. **Python 3.13** — [python.org/downloads](https://www.python.org/downloads/) (`python --version`)
2. **Node.js 20 or newer** — [nodejs.org](https://nodejs.org/) (`node --version`)
3. **PostgreSQL 16 or newer** — [postgresql.org/download](https://www.postgresql.org/download/) (`psql --version`).
   Remember the password you set for the `postgres` user during installation.

**Step 1 — get the code and the Python packages**

```bash
git clone https://github.com/dsservant28/voicelens.git
cd voicelens
python -m venv .venv                                  # a private Python environment for this project
.venv\Scripts\activate                                # Windows
# source .venv/bin/activate                           # macOS / Linux
pip install -r backend/requirements.txt
```

**Step 2 — create the database and tell VoiceLens where it is**

```bash
psql -U postgres -c "CREATE DATABASE voicelens;"      # asks for your postgres password
copy .env.example .env                                # Windows   (macOS / Linux: cp .env.example .env)
```

Open `.env` in any editor and set your password in the connection string:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/voicelens
```

**Step 3 — build everything with one command**

```bash
cd backend
python -m voicelens.pipeline --scale 1.0              # generate → validate → load → analyse → evaluate (about 4 minutes)
```

Use `--scale 0.25` for a quicker first run (under a minute). When it finishes it prints the headline results.

**Step 4 — start the API** (keep this terminal open)

```bash
python -m uvicorn voicelens.api.main:app --reload     # API docs at http://localhost:8000/docs
```

**Step 5 — start the app** (in a second terminal)

```bash
cd frontend
npm install                                           # first time only
npm run dev                                           # open http://localhost:5173
```

**To check everything** (from the repository root, with the environment activated):

```bash
python -m pytest -q                                   # 66 tests; API tests skip if PostgreSQL is not running
python scripts/policy_check.py                        # leakage, determinism and secrets rules
```

<details>
<summary><b>Each stage on its own, and options</b></summary>
<br/>

| Stage | Command (from `backend/`) |
|---|---|
| Generate | `python -m voicelens.generate --scale 1.0 --seed 20261022` |
| Validate | `python -m voicelens.validate` (add `--no-repro` to skip the generate-twice check) |
| Load | `python -m voicelens.db.load` |
| Analyse (stages 1–8) | `python -m voicelens.analyze --tau 0.6` |
| Evaluate | `python -m voicelens.evaluate` |
| Data dictionary | `python -m voicelens.generate.contract` |

- **Scale:** `1.0` is the full volume; `0.25` is a quick run; `0.02` matches `data/sample/`.
- **Outputs:** generated files go to `data/output/` (not committed — reproducible from the seed); reports are copied to
  `docs/results/`.
- **Reloading resets history:** the pipeline rebuilds the database, which clears review and action history. The
  **Recompute metrics** button on the Review page re-runs only the evaluation and keeps history.
- **Deep links:** `?theme=light`, `?why=ACT-000001` (opens the Why? drawer), `/review?tab=uncertain`.

</details>

<details>
<summary><b>Troubleshooting</b></summary>
<br/>

| Symptom | Fix |
|---|---|
| `Cannot reach PostgreSQL via DATABASE_URL` | PostgreSQL is not running, the database does not exist, or the password in `.env` is wrong |
| The app says **Backend not reachable** | Start the API (step 4) in a separate terminal |
| The app says **No data yet** | Run the pipeline (step 3) |
| `psql` is not recognised (Windows) | Add `C:\Program Files\PostgreSQL\<version>\bin` to your PATH, or use pgAdmin to create the database |

</details>

---

## 9. Reference

<details>
<summary><b>Requirements traceability</b></summary>
<br/>

| Requirement (problem statement) | Where it is met |
|---|---|
| Combine surveys, reviews and support text; themes; sentiment shifts; service priorities | Pulse, Priorities |
| Expose key decisions and exceptions; preserve traceability; measurable outputs | Why? drawer, Data flow, Proof |
| Master data first, valid parent IDs, exact ID formats | validator: `FK_MISSING` and `ID_FORMAT` only on planted anomalies |
| Taxonomies, balanced labels, neutral / mixed / sarcastic / ambiguous / multilingual text | generator, data dictionary, Proof slices |
| State changes as events, history not overwritten | `ticket_status_event`, `action_item_event`, `label_review_event` |
| Labels and outcomes from documented rules | template-decided gold labels |
| Step 1 — data dictionary | `docs/DATA_DICTIONARY.md` |
| Steps 2–4 — parents first, deterministic IDs, 50k reviews/responses + 20k messages, seed and scale | generator, Data flow |
| Step 5 — five labelled edge cases | `ground_truth/anomalies.csv`; Proof (200/200) |
| Step 6 — derived values computed | `DERIVED_MISMATCH` = 0 |
| Step 7 — separate ground truth, never in model input | `ground_truth/`, policy rules, leakage guard |
| Step 8 — validation | `validate/`, Data flow |
| Step 9 — CSV / JSON / SQL exports, README, dictionary, command, seed, manifest, validation summary | `data/sample/`, this README |
| Step 10 — regenerate twice and compare checksums | reproducibility check (byte-identical) |
| Acceptance — human-reviewed evaluation set, measurable metrics, privacy-safe text, traceable trends | Review (blind set), Proof, PII redaction, Pulse click-through |

</details>

<details>
<summary><b>API</b></summary>
<br/>

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` · `/meta` | status; products, themes, channels, latest run, lifecycle transitions |
| GET | `/overview` · `/pulse` · `/trend/items` | KPIs and trend; daily series; records behind a trend point |
| GET | `/alerts` · `/alerts/{id}` | alerts with magnitude; daily series and evidence |
| GET | `/lineage/{kind}/{id}` · `/trace/{id}` | lineage for an action, alert or cell; any ID resolved up and down |
| GET | `/themes` · `/themes/{product}/{theme}` | ranked priorities; weekly cells |
| GET / POST | `/review-queue` · `/review/plane` · `/review/{type}/{id}` | uncertain queue or blind set; decision plane; submit a human label |
| GET / POST | `/action-items` · `/action-items/{id}` · `/action-items/{id}/status` | list, detail and history, lifecycle-checked status change |
| GET | `/data-quality` · `/flow` · `/evaluation` | validation, manifest and exceptions; reconciled Sankey; metrics |
| POST | `/evaluation/run` · `/pipeline/run` | recompute evaluation; rerun analysis and evaluation |

</details>

<details>
<summary><b>Repository layout</b></summary>
<br/>

```
backend/voicelens/
  generate/   data contract, taxonomy, templates, world (incidents), build, edge cases, export
  validate/   contract-driven checks, reproducibility, summary
  db/         engine (.env), tables from the contract, COPY loader
  analyze/    normalize, lexicon, sentiment, themes, route, aggregate, detect, prioritize, actions
  evaluate/   metrics and report (the only reader of ground truth)
  api/        FastAPI app and routers
  pipeline.py one command for the whole flow
frontend/src/ api client, design system, layout, pages (Pulse, Priorities, Review, Flow, Proof)
tests/        66 tests: generator, validation, analysis, detection, evaluation, API, policy
docs/         architecture, data dictionary, decisions, results, images
data/sample/  small committed export
scripts/      policy_check.py
```

</details>

<div align="center">
<br/>
<sub>VoiceLens · synthetic data only · <a href="docs/ARCHITECTURE.md">architecture</a> · <a href="docs/DECISIONS.md">decisions</a> · <a href="docs/DATA_DICTIONARY.md">data dictionary</a></sub>
</div>
