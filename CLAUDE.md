# CLAUDE.md — VoiceLens (YottaFlex hackathon, 6 hours)

> Owner: Jagadeep Varma Penmetsa. Individual hackathon build. AI assistance is allowed and disclosed.
> The owner reviews and approves every change. Full spec: `docs/problem_statement.md`.

## 1. What we are building
**VoiceLens — customer feedback intelligence.** It combines survey responses, product reviews and support
messages, finds recurring **themes**, tracks **sentiment shifts** over time, and turns them into prioritised
**action items** — with every number traceable back to the source records.

Four parts:
- **A. Generator** — deterministic synthetic data (seed 20261022, `--scale`): customers, products, channels,
  surveys, survey responses, reviews, support tickets + messages; balanced sentiment/theme labels; neutral, mixed,
  sarcastic, ambiguous and multilingual text; 5 labelled edge cases; separate `ground_truth` files.
- **B. Validation** — PK/FK/enum/date/arithmetic/lifecycle/duplicate checks + reproducibility (run twice, compare checksums).
- **C. Analysis** — PII redaction → sentiment + theme classification (explainable, rule/lexicon based) →
  weekly trends and sentiment-shift detection → priority scores → action items (rule-based, with evidence).
- **D. Evaluation + app** — metrics vs a human-reviewed evaluation set; FastAPI backend; React dashboard.

## 2. Hard rules (never break)
1. **No label leakage.** Code in `backend/voicelens/analyze/` must never read ground truth or gold labels
   (`ground_truth`, `issue_type`, `true_sentiment`, `true_theme`, `gold_label`, `human_label`). Only
   `backend/voicelens/evaluate/` may. Enforced by `scripts/policy_check.py` (hook + test).
   Never add `# policy: allow` without the owner's approval.
2. **Determinism.** Generator randomness only from one `numpy.random.default_rng(seed)` passed down. No `import random`,
   no global `np.random.*`, no `datetime.now()` / `date.today()` in generator code. Fixed reference date instead.
3. **Parents before children.** Master data first (Customer, Product, Channel, Survey, Theme taxonomy), then children
   with valid parent IDs — except deliberately planted, labelled edge cases.
4. **Derived values are computed** (counts, scores, sentiment shares, priority, statuses, dates), never randomly generated.
5. **History is append-only.** State changes (action item status, label reviews, ticket status) are new rows in `*_events` tables.
6. **Labels come from documented generation rules** (the template that produced the text), never random assignment.
7. **Exact IDs:** `SUR-2026-000001`, `RESP-<survey-id>-001`, `REV-2026-000001`, `MSG-<ticket-id>-001`, `THEME-000001`.
   Zero-padded, immutable, identical across files. Other entity IDs: see `docs/DECISIONS.md`.
8. **Privacy-safe.** All text synthetic. No real personal data. PII in text is detected and redacted before analysis.
9. **Traceability.** Every trend point, theme count, priority and action item links to the source record IDs behind it.
10. **No secrets in code.** DB URL/password come from `.env` (git-ignored); `.env.example` has placeholders.

## 3. Layout (keep to this)
```
backend/
  voicelens/
    generate/   # synthetic data generator (seeded, scale param)
    validate/   # data checks + reproducibility
    analyze/    # PII redaction, sentiment, themes, trends, priorities, action items (NO ground truth)
    evaluate/   # metrics vs ground truth / human-reviewed eval set
    db/         # SQLAlchemy models, schema, loading
    api/        # FastAPI app and routes
  requirements.txt
frontend/       # React + Vite + TypeScript + Tailwind
tests/          # pytest (root pytest.ini sets pythonpath=backend)
data/           # generated outputs (git-ignored except a small sample if decided)
docs/  scripts/
```

## 4. Stack
Windows. Python 3.13, FastAPI, SQLAlchemy 2 + psycopg 3, PostgreSQL 18 (local), pandas/numpy, pytest.
React (Vite + TS), react-router, axios, @tanstack/react-query, recharts, Tailwind. No paid APIs. No heavy ML libraries.

## 5. How to work with me
- **Plan first** for anything non-trivial; wait for approval. Small steps, each with a quick test.
- **Time-boxed (6 hours):** prefer the simplest thing that meets the requirement; say when something is a stretch goal.
- Record design choices in `docs/DECISIONS.md` (decision, options, why, trade-off).
- **Never commit or push**; the owner commits after reviewing.
- Before saying "done", run `python scripts/policy_check.py` and `pytest -q`. Don't claim anything you didn't run.
