# Validation summary - PASS_WITH_EXCEPTIONS

Data `C:\CandidateWorkspace\voicelens\data\output` · seed 20261022 · scale 1.0 · validated 2026-11-15 18:21:48  
147,488 rows checked · 132 exceptions · 120 rows quarantined (kept in DB, excluded from analysis)

## Reproducibility

Generated twice (seed 20261022, scale 1.0): 31 files, identical = **True**; matches validated data = **True** (65.2 s).

## File integrity (manifest reconciliation)

| Table | Rows (manifest) | Rows (file) | Checksum | Columns |
|---|---:|---:|---|---|
| customer | 10,000 | 10,000 | ok | ok |
| product | 12 | 12 | ok | ok |
| channel | 6 | 6 | ok | ok |
| survey | 51 | 51 | ok | ok |
| theme | 12 | 12 | ok | ok |
| survey_response | 20,040 | 20,040 | ok | ok |
| review | 30,000 | 30,000 | ok | ok |
| support_ticket | 5,128 | 5,128 | ok | ok |
| support_message | 20,424 | 20,424 | ok | ok |
| ticket_status_event | 21,955 | 21,955 | ok | ok |
| sentiment_label | 17,773 | 17,773 | ok | ok |
| feedback_theme | 22,087 | 22,087 | ok | ok |

## Tables

| Table | Rows | With exceptions | Quarantined | Clean |
|---|---:|---:|---:|---:|
| customer | 10,000 | 0 | 0 | 10,000 |
| product | 12 | 0 | 0 | 12 |
| channel | 6 | 0 | 0 | 6 |
| survey | 51 | 0 | 0 | 51 |
| theme | 12 | 0 | 0 | 12 |
| survey_response | 20,040 | 59 | 59 | 19,981 |
| review | 30,000 | 33 | 21 | 29,967 |
| support_ticket | 5,128 | 0 | 0 | 5,128 |
| support_message | 20,424 | 0 | 0 | 20,424 |
| ticket_status_event | 21,955 | 0 | 0 | 21,955 |
| sentiment_label | 17,773 | 0 | 0 | 17,773 |
| feedback_theme | 22,087 | 40 | 40 | 22,047 |

## Exceptions by type

| Exception type | Disposition | Count |
|---|---|---:|
| DUPLICATE_RESPONSE | QUARANTINE | 40 |
| TEST_LABEL_IN_MODEL_INPUT | QUARANTINE | 40 |
| THEME_OUTSIDE_TAXONOMY | QUARANTINE | 40 |
| DUPLICATE_REVIEW | FLAG | 12 |

## Checks

| Check | Category | Disposition | Exceptions | Rule |
|---|---|---|---:|---|
| REQUIRED_MISSING | validity | QUARANTINE | 0 | required field is empty |
| TYPE_INVALID | validity | QUARANTINE | 0 | value does not parse as the contract type (int/float/date/datetime) |
| ENUM_INVALID | validity | QUARANTINE | 0 | value not in the contract's allowed list |
| ID_FORMAT | validity | QUARANTINE | 0 | ID does not match its zero-padded pattern |
| TAG_UNKNOWN | validity | FLAG | 40 | tags contains a value outside the source-tag vocabulary |
| PK_DUPLICATE | integrity | QUARANTINE | 0 | primary key repeats (first occurrence kept) |
| UNIQUE_VIOLATION | integrity | FLAG | 0 | a unique non-key field repeats |
| FK_MISSING | integrity | QUARANTINE | 40 | foreign key (incl. polymorphic source_id) has no parent row |
| DATE_ORDER | temporal | FLAG | 0 | dates out of order or outside the feedback window |
| DERIVED_MISMATCH | reconciliation | FLAG | 0 | a derived value does not equal its recomputation |
| LIFECYCLE_ILLEGAL | lifecycle | FLAG | 0 | status transition not allowed by the contract lifecycle |
| DUPLICATE_RESPONSE | duplicate | QUARANTINE | 40 | same customer answered the same survey again (first kept) |
| DUPLICATE_REVIEW | duplicate | FLAG | 12 | same customer posted the same text for the same product |

## Examples (first 2 per type)

| Exception | Table | Key | Detail |
|---|---|---|---|
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000002-350 | duplicate of RESP-SUR-2026-000002-153 (same text) |
| DUPLICATE_RESPONSE | survey_response | RESP-SUR-2026-000003-562 | duplicate of RESP-SUR-2026-000003-028 (same text) |
| DUPLICATE_REVIEW | review | REV-2026-001210 | repeated review text |
| DUPLICATE_REVIEW | review | REV-2026-002027 | repeated review text |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-000671 | label-like tag 'eval_label=negative' in model input |
| TEST_LABEL_IN_MODEL_INPUT | review | REV-2026-001466 | label-like tag 'eval_label=neutral' in model input |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-000724|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
| THEME_OUTSIDE_TAXONOMY | feedback_theme | review|REV-2026-002054|THEME-000999|source_system | theme_id='THEME-000999' not found in theme |
