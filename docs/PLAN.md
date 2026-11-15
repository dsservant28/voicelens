# VoiceLens — build plan (agreed before coding)

Goal: in 6 hours, ship a working 3-tier app (React → FastAPI → PostgreSQL) that turns synthetic customer
feedback into themes, sentiment trends, shift alerts, priorities and action items, with traceability,
validation, exceptions and measurable evaluation.

## 1. Data model (PostgreSQL)

### Master data
| Table | PK format | Key fields |
|---|---|---|
| `customer` | `CUST-000001` | segment (consumer/smb/enterprise), region, preferred_language, created_at |
| `product` | `PROD-0001` | name, category (taxonomy), launched_at, status |
| `channel` | `CHAN-01` | name (web, app_store, email, chat, phone, social), type (survey/review/support) |
| `survey` | `SUR-2026-000001` | name, product_id (FK, optional), channel_id (FK), opens_at, closes_at, status |
| `theme` | `THEME-000001` | code, name, parent_theme_id (FK self, optional), keywords, severity_weight, effective_from |

### Feedback (children)
| Table | PK format | FKs | Notes |
|---|---|---|---|
| `survey_response` | `RESP-<survey-id>-001` (e.g. `RESP-SUR-2026-000001-001`, counter per survey) | survey_id, customer_id, product_id | score 0–10 (NPS-style), text, language, submitted_at |
| `review` | `REV-2026-000001` | customer_id, product_id, channel_id | rating 1–5, text, language, posted_at |
| `support_ticket` | `TKT-2026-000001` | customer_id, product_id, channel_id | status lifecycle, opened_at, closed_at |
| `support_message` | `MSG-<ticket-id>-001` (e.g. `MSG-TKT-2026-000001-001`, counter per ticket) | ticket_id | sender (customer/agent), text, language, sent_at |

### Labels, themes, actions
| Table | PK | Notes |
|---|---|---|
| `sentiment_label` | `LBL-000001` | source_type + source_id, sentiment (positive/negative/neutral/mixed), labeler (generator_rule / model / human), split (train/eval), label_note |
| `feedback_theme` (bridge, N:M) | (source_type, source_id, theme_id, labeler) | one text can have several themes |
| `action_item` | `ACT-000001` | theme_id, product_id, priority_score, status, owner_role, evidence_count, created_from_rule |
| `action_item_event` | `AIE-000001` | action_item_id, from_status, to_status, actor, note, at — append-only |
| `label_review_event` | `LRE-000001` | label_id, old, new, reviewer, at — append-only (human review of eval set) |
| `ticket_status_event` | `TSE-000001` | ticket_id, from_status, to_status, at — append-only |
| `data_exception` | `EXC-000001` | source_type, source_id, exception_type, detail, detected_at, resolution_status |

Cardinality: customer 1:N responses/reviews/tickets; survey 1:N responses; ticket 1:N messages;
product 1:N reviews/responses/tickets; feedback N:M theme via `feedback_theme`; theme 1:N action items;
action item 1:N events. Optional: survey.product_id, theme.parent_theme_id, ticket.closed_at.

Lifecycles:
- ticket: OPEN → IN_PROGRESS → RESOLVED → CLOSED (REOPENED → IN_PROGRESS allowed)
- action item: OPEN → IN_PROGRESS → DONE | DISMISSED
- survey: DRAFT → OPEN → CLOSED

## 2. Generator (deterministic, seed 20261022, `--scale`)
- Volume at scale 1.0: 50,000 reviews + survey responses (e.g. 30,000 reviews + 20,000 responses), 20,000 support messages.
- Text = templates: theme phrase × sentiment frame × product/channel slots. The **template decides the label**
  (documented rule), so labels are never random.
- Coverage: positive / negative / neutral / **mixed** ("love the app but billing is a mess"), **sarcasm**
  ("Oh great, another 3-day delay. Just perfect."), **ambiguous**, **multilingual** (Hindi, Telugu, Spanish samples).
- Balanced labels across sentiment and themes; dates spread over ~6 months with **planted sentiment shifts**
  (e.g. delivery complaints for one product rise sharply in a known week) — recorded in ground truth.
- 5 labelled edge cases (in `ground_truth/anomalies.csv`, never in input files):
  1. `LABEL_CONTRADICTS_TEXT` — stored label says positive, text is clearly negative, no label_note.
  2. `DUPLICATE_RESPONSE` — same customer + survey + text submitted twice.
  3. `PII_LEAK` — text contains a (fake) email/phone/name of a customer.
  4. `THEME_OUTSIDE_TAXONOMY` — feedback_theme points to a theme code not in the taxonomy.
  5. `TEST_LABEL_IN_MODEL_INPUT` — an eval-split gold label is copied into an input column/text.
- Outputs: CSV + JSON + SQL seed, `ground_truth/` folder, data dictionary, manifest (files, rows, SHA-256), validation summary.

## 3. Validation
PK uniqueness, FK integrity, enums, date ordering (survey open ≤ response ≤ close; ticket opened ≤ messages ≤ closed),
arithmetic reconciliation (counts/aggregates match sources), lifecycle transitions legal, duplicates.
Failing rows go to `data_exception` (exception path) — nothing crashes. Reproducibility: generate twice → identical checksums.

## 4. Analysis pipeline (explainable; reads inputs only, never ground truth)
1. **PII redaction** (regex for email/phone + known-name check) → redacted text + `PII_LEAK` exception.
2. **Leakage guard** — refuses any input column that holds eval labels → `TEST_LABEL_IN_MODEL_INPUT` exception.
3. **Sentiment** — multilingual lexicon + negation + contrast words ("but") for mixed + sarcasm cues; returns label + matched evidence words + confidence.
4. **Themes** — keyword/phrase matching against the taxonomy; unknown theme codes → `THEME_OUTSIDE_TAXONOMY` exception.
5. **Label checks** — stored label vs model prediction with high confidence disagreement → `LABEL_CONTRADICTS_TEXT` flag for review.
6. **Trends** — weekly sentiment share per product × theme; **shift** = change in negative share vs trailing 4-week baseline above threshold.
7. **Priority score** (documented formula) = volume × negative share × severity_weight × (1 + shift).
8. **Action items** — rule: theme × product with ≥ N negative mentions in 2 weeks and a positive shift → create/refresh action item with evidence IDs.

## 5. Evaluation
- Eval split (e.g. 2,000 items) with **human-reviewed labels** (generator gold labels confirmed/overridden through the review screen; reviews logged in `label_review_event`).
- Metrics: sentiment accuracy + macro-F1 + per-class precision/recall + confusion matrix; theme micro/macro-F1;
  anomaly detection recall/precision per edge case; shift detection hit rate vs planted shifts.

## 6. API (FastAPI)
`GET /health` · `GET /summary` · `GET /trends?product=&theme=` · `GET /themes` · `GET /themes/{id}/evidence` ·
`GET /priorities` · `GET /action-items` · `POST /action-items/{id}/status` · `GET /feedback/{source_type}/{id}` ·
`GET /review-queue` · `POST /labels/{id}/review` · `GET /exceptions` · `GET /metrics` · `GET /validation`

## 7. Screens (React)
1. **Overview** — KPIs, sentiment trend chart, top shift alerts.
2. **Themes & priorities** — ranked table → drill-down to source records (traceability).
3. **Action items** — board/table with status changes (events shown as history).
4. **Review queue** — human review of eval labels and flagged contradictions.
5. **Data quality** — validation summary + exceptions by type.
6. **Evaluation** — metrics + confusion matrix.

## 8. Timeline (6 hours — adjust to actual end time)
| Block | Work |
|---|---|
| 0:00–0:20 | Setup: folder, git, harness, venv, Postgres DB, Vite app, first commit |
| 0:20–1:30 | Data dictionary + generator + edge cases + ground truth (small scale first) |
| 1:30–2:00 | Validation + reproducibility + exports + load into Postgres |
| 2:00–3:00 | Analysis pipeline + evaluation metrics |
| 3:00–4:30 | FastAPI endpoints + React screens |
| 4:30–5:15 | Full-scale run, README, DECISIONS, AI disclosure, prompts README |
| 5:15–5:45 | Fresh-run test, demo rehearsal |
| 5:45–6:00 | Buffer + submit |

Cut order if behind: multilingual depth → review queue UI → action-item board UI (keep API) → charts polish.
Never cut: generator correctness, edge cases + ground truth, validation, evaluation metrics, traceability.
