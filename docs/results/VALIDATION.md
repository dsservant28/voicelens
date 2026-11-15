# Validation summary - PASS_WITH_EXCEPTIONS

Data `C:\CandidateWorkspace\voicelens\data\output` · seed 20261022 · scale 0.25 · validated 2026-11-15 16:23:06  
36,479 rows checked · 32 exceptions · 30 rows quarantined (kept in DB, excluded from analysis)

## Reproducibility

Skipped (--no-repro).

## File integrity (manifest reconciliation)

| Table | Rows (manifest) | Rows (file) | Checksum | Columns |
|---|---:|---:|---|---|
| customer | 2,500 | 2,500 | ok | ok |
| product | 12 | 12 | ok | ok |
| channel | 6 | 6 | ok | ok |
| survey | 14 | 14 | ok | ok |
| theme | 12 | 12 | ok | ok |
| survey_response | 5,010 | 5,010 | ok | ok |
| review | 7,500 | 7,500 | ok | ok |
| support_ticket | 1,250 | 1,250 | ok | ok |
| support_message | 5,003 | 5,003 | ok | ok |
| ticket_status_event | 5,331 | 5,331 | ok | ok |
| sentiment_label | 4,426 | 4,426 | ok | ok |
| feedback_theme | 5,415 | 5,415 | ok | ok |

## Tables

| Table | Rows | With exceptions | Quarantined | Clean |
|---|---:|---:|---:|---:|
| customer | 2,500 | 0 | 0 | 2,500 |
| product | 12 | 0 | 0 | 12 |
| channel | 6 | 0 | 0 | 6 |
| survey | 14 | 0 | 0 | 14 |
| theme | 12 | 0 | 0 | 12 |
| survey_response | 5,010 | 13 | 13 | 4,997 |
| review | 7,500 | 9 | 7 | 7,491 |
| support_ticket | 1,250 | 0 | 0 | 1,250 |
| support_message | 5,003 | 0 | 0 | 5,003 |
| ticket_status_event | 5,331 | 0 | 0 | 5,331 |
| sentiment_label | 4,426 | 0 | 0 | 4,426 |
| feedback_theme | 5,415 | 10 | 10 | 5,405 |

## Exceptions by type

| Exception type | Disposition | Count |
|---|---|---:|
| DUPLICATE_RESPONSE | QUARANTINE | 10 |
| TEST_LABEL_IN_MODEL_INPUT | QUARANTINE | 10 |
| THEME_OUTSIDE_TAXONOMY | QUARANTINE | 10 |
| DUPLICATE_REVIEW | FLAG | 2 |

## Checks

| Check | Category | Disposition | Exceptions | Rule |
|---|---|---|---:|---|
| REQUIRED_MISSING | validity | QUARANTINE | 0 | required field is empty |
| TYPE_INVALID | validity | QUARANTINE | 0 | value does not parse as the contract type (int/float/date/datetime) |
| ENUM_INVALID | validity | QUARANTINE | 0 | value not in the contract's allowed list |
| ID_FORMAT | validity | QUARANTINE | 0 | ID does not match its zero-padded pattern |
| TAG_UNKNOWN | validity | FLAG | 10 | tags contains a value outside the source-tag vocabulary |
| PK_DUPLICATE | integrity | QUARANTINE | 0 | primary key repeats (first occurrence kept) |
| UNIQUE_VIOLATION | integrity | FLAG | 0 | a unique non-key field repeats |
| FK_MISSING | integrity | QUARANTINE | 10 | foreign key (incl. polymorphic source_id) has no parent row |
| DATE_ORDER | temporal | FLAG | 0 | dates out of order or outside the feedback window |
| DERIVED_MISMATCH | reconciliation | FLAG | 0 | a derived value does not equal its recomputation |
| LIFECYCLE_ILLEGAL | lifecycle | FLAG | 0 | status transition not allowed by the contract lifecycle |
| DUPLICATE_RESPONSE | duplicate | QUARANTINE | 10 | same customer answered the same survey again (first kept) |
| DUPLICATE_REVIEW | duplicate | FLAG | 2 | same customer posted the same text for the same product |

## Examples (first 2 per type)

| Exception | Table | Key | Detail |
|---|---|---|---|
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000001-471 | duplicate of RESP-SUR-2026-000001-086 (same text) |
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000001-472 | duplicate of RESP-SUR-2026-000001-108 (same text) |
| DUPLICATE_REVIEW | review | REV-2026-003431 | repeated review text |
| DUPLICATE_REVIEW | review | REV-2026-005396 | repeated review text |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-001263 | label-like tag 'eval_label=negative' in model input |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-001853 | label-like tag 'eval_label=positive' in model input |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-001885|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-002377|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
