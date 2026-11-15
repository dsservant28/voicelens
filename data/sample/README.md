# VoiceLens data sample (scale 0.02)

A small, committed export of the synthetic dataset so it can be inspected without running anything.
The full dataset (scale 1.0: 30,000 reviews + 20,000 survey responses + 20,000 support messages) is
reproducible from the same generator and seed.

**Regenerate this sample** (from `backend/`):

```
python -m voicelens.generate --scale 0.02 --seed 20261022 --out ../data/sample
python -m voicelens.validate --data ../data/sample
```

Fixed seed `20261022`, reference date `2026-10-01`, feedback window `2026-04-06 .. 2026-09-27`.
Same seed + scale ⇒ byte-identical files (SHA-256 per file in `manifest.json`; the validator regenerates twice and compares).

| Path | Content |
|---|---|
| `csv/`, `json/` | the 12 input tables (customer, product, channel, survey, theme, survey_response, review, support_ticket, support_message, ticket_status_event, sentiment_label, feedback_theme) |
| `sql/seed.sql` | `CREATE TABLE` (generated from the data contract) + `INSERT`s; foreign keys added `NOT VALID` so planted anomalies load and are reported |
| `ground_truth/` | evaluation only - `labels` (gold sentiment/theme per item, style, language, template, split), `incidents` (hidden causes of sentiment shifts with per-channel lag), `anomalies` (the 5 planted edge cases with expected decisions). Never read by the analysis code. |
| `manifest.json` | generator command, seed, scale, volumes, row count + SHA-256 per file |
| `validation/` | validation summary (`.md` / `.json`) and the `data_exception` rows (quarantine / flag) |

Field definitions, PK/FK, cardinality, lifecycles and validation rules: [`docs/DATA_DICTIONARY.md`](../../docs/DATA_DICTIONARY.md).
