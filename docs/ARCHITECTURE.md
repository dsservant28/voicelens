# VoiceLens — Architecture

## 1. Pitch (one paragraph for the panel)
Customer feedback is a **sensor network**: problems surface in support tickets first, then reviews, then surveys.
VoiceLens is an **early-warning system**, not a dashboard. It detects the **root cause early**, says **how confident**
it is, routes uncertain cases to a **human reviewer**, and proves every number with **source records**. Because the
data comes from a simulated world with hidden incidents, we can measure **time-to-detect**, not only accuracy.

## 2. Three tiers
- **Frontend:** React + Vite + TypeScript, Tailwind, react-query, recharts.
- **Backend:** FastAPI (one router per stage) + Python pipeline package `voicelens`.
- **Database:** PostgreSQL 18, schema layers `raw` → `curated` → `insight` → `event` (or table prefixes if schemas slow us down).

## 3. Pipeline (9 stages, each a pure function with a typed input/output)
| # | Stage | Module | Input → Output | Key rule |
|---|---|---|---|---|
| 1 | Ingest gate | `validate/` | generated CSV → raw tables + `data_exception` | Contract checks (PK, FK, enum, dates, duplicates). Bad rows are **quarantined, not dropped** (exception path). |
| 2 | Normalize | `analyze/normalize.py` | raw text → curated text | PII redaction (email, phone, known customer names) → `PII_LEAK` exception; language tag; leakage guard rejects any `eval_label` in inputs → `TEST_LABEL_IN_MODEL_INPUT`. |
| 3 | Analyze | `analyze/sentiment.py`, `analyze/themes.py` | curated text → prediction | Lexicon + negation ("not bad") + contrast ("but" → mixed) + sarcasm cues + Hinglish/hi/te/es lexicons. Returns **label, confidence (0–1), evidence tokens, rule ids**. Themes via taxonomy keywords; unknown theme codes → `THEME_OUTSIDE_TAXONOMY`. Stored label vs confident prediction disagree → `LABEL_CONTRADICTS_TEXT` flag. |
| 4 | Abstain | `analyze/route.py` | prediction → auto / review | confidence < τ (default 0.6) or style cues (sarcasm/mixed/code-mixed) → **review queue**. Never guess silently. |
| 5 | Aggregate | `analyze/aggregate.py` | predictions → weekly cube | product × theme × channel × ISO week: volume, negative share, mean score/rating. Each cell keeps the list of contributing source IDs (lineage). |
| 6 | Detect | `analyze/detect.py` | cube → alerts | Shift = negative share this week − trailing 4-week baseline; alert if shift ≥ δ and volume ≥ n_min. Records **first channel to move** (lead-lag) and evidence IDs. |
| 7 | Prioritize | `analyze/prioritize.py` | alerts → priority | `priority = volume × neg_share × severity_weight × (1 + shift)`; formula and inputs stored with the score. |
| 8 | Act | `analyze/actions.py` | priorities → action items | Rule: priority ≥ P and alert active ≥ 1 week → create/refresh `action_item` with evidence; lifecycle OPEN → IN_PROGRESS → DONE / DISMISSED via append-only `action_item_event`. |
| 9 | Evaluate | `evaluate/` | predictions + alerts vs ground truth | Sentiment accuracy / macro-F1 / confusion matrix; theme F1; **slice metrics** by style + language; **accuracy vs coverage** at τ; edge-case recall per `issue_type`; incident **detection rate, false alarms, mean time-to-detect (days)**. |

The human review loop: reviewer confirms/corrects a label in the UI → `label_review_event` (append-only) → those items form the
**human-reviewed evaluation set** required by the acceptance criteria.

## 4. Three differentiators
1. **Root-cause early warning** — alerts are compared to hidden incidents: "detected 4/4, mean 3.5 days after onset, 1 false alarm";
   shows that support tickets lead reviews and surveys.
2. **Honest AI** — confidence + abstention + human-in-the-loop; reports accuracy vs coverage and per-slice weaknesses (sarcasm, Telugu, Hinglish).
3. **"Why this number?" lineage** — every alert, priority and action item drills down to the weekly cell → feedback items → redacted text → rules fired.
   Stretch: closed-loop verification (after an action item is DONE, check whether sentiment recovered).

## 5. API (FastAPI)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + DB check |
| GET | `/overview` | KPIs, sentiment trend, top alerts |
| GET | `/alerts` · `/alerts/{id}` | detected shifts with evidence + lead channel |
| GET | `/lineage/{kind}/{id}` | "Why?" chain for alert / action / cell |
| GET | `/feedback/{source_type}/{id}` | one record, redacted text, prediction, rules fired |
| GET | `/review-queue` · POST `/review/{source_type}/{id}` | abstained items; submit human label (event) |
| GET | `/action-items` · POST `/action-items/{id}/status` | list; status change (event) |
| GET | `/data-quality` | validation summary + exceptions by type |
| GET | `/evaluation` | all metrics incl. slices, coverage curve, time-to-detect |
| POST | `/pipeline/run` | admin: rerun stages 2–9 (idempotent) |

## 6. Screens (React)
1. **Overview** — KPIs, sentiment trend by channel, top alerts.
2. **Alerts & root cause** — alert list, lead-lag chart (tickets vs reviews vs surveys), "Why?" drawer.
3. **Review queue** — abstained/flagged items, confirm or correct (writes events).
4. **Action items** — table with status buttons and event history.
5. **Data quality** — validation results, exceptions by type with expected vs actual decision.
6. **Evaluation** — metrics, confusion matrix, slice table, accuracy-vs-coverage chart, incident detection table.

## 7. Build order (cut from the bottom if late)
1. Generator (in progress) → 2. Validate + load to Postgres → 3. Normalize + analyze + abstain →
4. Aggregate + detect + prioritize + act → 5. Evaluate → 6. API → 7. Screens 1, 2, 6 → 8. Screens 3, 4, 5 → 9. Docs.
Never cut: edge cases + ground truth, validation, evaluation numbers, lineage on alerts.
