# Validation summary - PASS_WITH_EXCEPTIONS

Data `..\data\sample` · seed 20261022 · scale 0.02 · validated 2026-11-15 17:59:42  
2,944 rows checked · 11 exceptions · 9 rows quarantined (kept in DB, excluded from analysis)

## Reproducibility

Generated twice (seed 20261022, scale 0.02): 31 files, identical = **True**; matches validated data = **True** (5.7 s).

## File integrity (manifest reconciliation)

| Table | Rows (manifest) | Rows (file) | Checksum | Columns |
|---|---:|---:|---|---|
| customer | 200 | 200 | ok | ok |
| product | 12 | 12 | ok | ok |
| channel | 6 | 6 | ok | ok |
| survey | 5 | 5 | ok | ok |
| theme | 12 | 12 | ok | ok |
| survey_response | 403 | 403 | ok | ok |
| review | 600 | 600 | ok | ok |
| support_ticket | 100 | 100 | ok | ok |
| support_message | 397 | 397 | ok | ok |
| ticket_status_event | 420 | 420 | ok | ok |
| sentiment_label | 354 | 354 | ok | ok |
| feedback_theme | 435 | 435 | ok | ok |

## Tables

| Table | Rows | With exceptions | Quarantined | Clean |
|---|---:|---:|---:|---:|
| customer | 200 | 0 | 0 | 200 |
| product | 12 | 0 | 0 | 12 |
| channel | 6 | 0 | 0 | 6 |
| survey | 5 | 0 | 0 | 5 |
| theme | 12 | 0 | 0 | 12 |
| survey_response | 403 | 3 | 3 | 400 |
| review | 600 | 5 | 3 | 595 |
| support_ticket | 100 | 0 | 0 | 100 |
| support_message | 397 | 0 | 0 | 397 |
| ticket_status_event | 420 | 0 | 0 | 420 |
| sentiment_label | 354 | 0 | 0 | 354 |
| feedback_theme | 435 | 3 | 3 | 432 |

## Exceptions by type

| Exception type | Disposition | Count |
|---|---|---:|
| DUPLICATE_RESPONSE | QUARANTINE | 3 |
| TEST_LABEL_IN_MODEL_INPUT | QUARANTINE | 3 |
| THEME_OUTSIDE_TAXONOMY | QUARANTINE | 3 |
| DUPLICATE_REVIEW | FLAG | 2 |

## Checks

| Check | Category | Disposition | Exceptions | Rule |
|---|---|---|---:|---|
| REQUIRED_MISSING | validity | QUARANTINE | 0 | required field is empty |
| TYPE_INVALID | validity | QUARANTINE | 0 | value does not parse as the contract type (int/float/date/datetime) |
| ENUM_INVALID | validity | QUARANTINE | 0 | value not in the contract's allowed list |
| ID_FORMAT | validity | QUARANTINE | 0 | ID does not match its zero-padded pattern |
| TAG_UNKNOWN | validity | FLAG | 3 | tags contains a value outside the source-tag vocabulary |
| PK_DUPLICATE | integrity | QUARANTINE | 0 | primary key repeats (first occurrence kept) |
| UNIQUE_VIOLATION | integrity | FLAG | 0 | a unique non-key field repeats |
| FK_MISSING | integrity | QUARANTINE | 3 | foreign key (incl. polymorphic source_id) has no parent row |
| DATE_ORDER | temporal | FLAG | 0 | dates out of order or outside the feedback window |
| DERIVED_MISMATCH | reconciliation | FLAG | 0 | a derived value does not equal its recomputation |
| LIFECYCLE_ILLEGAL | lifecycle | FLAG | 0 | status transition not allowed by the contract lifecycle |
| DUPLICATE_RESPONSE | duplicate | QUARANTINE | 3 | same customer answered the same survey again (first kept) |
| DUPLICATE_REVIEW | duplicate | FLAG | 2 | same customer posted the same text for the same product |

## Examples (first 2 per type)

| Exception | Table | Key | Detail |
|---|---|---|---|
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000001-117 | duplicate of RESP-SUR-2026-000001-099 (same text) |
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000002-127 | duplicate of RESP-SUR-2026-000002-113 (same text) |
| DUPLICATE_REVIEW | review | REV-2026-000470 | repeated review text |
| DUPLICATE_REVIEW | review | REV-2026-000548 | repeated review text |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-000387 | label-like tag 'eval_label=negative' in model input |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-000425 | label-like tag 'eval_label=negative' in model input |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-000056|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-000146|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
