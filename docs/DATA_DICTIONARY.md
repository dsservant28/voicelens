# VoiceLens data dictionary

> Generated from `backend/voicelens/generate/contract.py` (single source of truth; the validator uses the same contract).
> Regenerate: `python -m voicelens.generate.contract` (from `backend/`).

Conventions: IDs are zero-padded and immutable and identical across files. Dates are ISO `YYYY-MM-DD`, datetimes are `YYYY-MM-DD HH:MM:SS` (synthetic local time). Reference date ("today") = 2026-10-01. Feedback window = 2026-04-06 .. 2026-09-27 (25 ISO weeks). All text is synthetic.

## Relationships and cardinality

| Child.field | Parent | Cardinality | Optional | Note |
|---|---|---|---|---|
| survey.channel_id | channel | N:1 | no |  |
| survey.product_id | product | N:1 | yes |  |
| theme.parent_theme_id | theme | N:1 (self) | yes |  |
| survey_response.survey_id | survey | N:1 | no |  |
| survey_response.customer_id | customer | N:1 | no |  |
| survey_response.product_id | product | N:1 | no |  |
| review.customer_id | customer | N:1 | no |  |
| review.product_id | product | N:1 | no |  |
| review.channel_id | channel | N:1 | no |  |
| support_ticket.customer_id | customer | N:1 | no |  |
| support_ticket.product_id | product | N:1 | no |  |
| support_ticket.channel_id | channel | N:1 | no |  |
| support_message.ticket_id | support_ticket | N:1 | no |  |
| ticket_status_event.ticket_id | support_ticket | N:1 | no |  |
| sentiment_label.source_id | review / survey_response / support_message | N:1 | no | polymorphic via source_type |
| feedback_theme.theme_id | theme | N:1 | no |  |
| feedback_theme.source_id | review / survey_response / support_message | N:1 | no | feedback N:M theme |
| action_item.theme_id | theme | N:1 | no |  |
| action_item.product_id | product | N:1 | no |  |
| action_item_event.action_item_id | action_item | N:1 | no |  |
| label_review_event.source_id | review / survey_response / support_message | N:1 | no | polymorphic |
| feedback_item.customer_id | customer | N:1 | no |  |
| feedback_item.product_id | product | N:1 | no |  |
| feedback_item.channel_id | channel | N:1 | no |  |
| feedback_item.run_id | pipeline_run | N:1 | no |  |
| feedback_item.source_id | review / survey_response / support_message | 1:1 | no | polymorphic |
| prediction.run_id | pipeline_run | N:1 | no |  |
| prediction.source_id | feedback_item | 1:1 | no | same (source_type, source_id) |

Derived N:M: feedback N:M theme via `feedback_theme`. 1:N summary: customer 1:N reviews/responses/tickets; survey 1:N responses; ticket 1:N messages and 1:N status events; theme 1:N action items; action item 1:N events.

## Master data

### `customer`

A customer/prospect who gives feedback. Synthetic identity (fake name, example.com email, 555-01xx phone).

- **Primary key:** customer_id
- **Effective dates:** created_at (account creation; always before any of the customer's feedback).
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| customer_id | id | yes |  |  | yes |  | CUST-000001, zero-padded, immutable |
| display_name | str | yes |  |  |  |  | synthetic 'First Last'; PII - must be redacted if it appears in text |
| email | str | yes |  |  | yes |  | <first>.<last><n>@example.com (reserved domain); PII |
| phone | str | yes |  |  |  |  | +1-555-01NN fictional range; not unique; PII |
| segment | enum | yes | consumer, smb, enterprise |  |  |  |  |
| region | enum | yes | IN-North, IN-South, IN-East, IN-West, International |  |  |  |  |
| preferred_language | enum | yes | en, es, hi, te, hi-Latn |  |  |  | the language the customer writes feedback in |
| created_at | date | yes |  |  |  |  | 2024-01-01 <= created_at < 2026-04-06 (window start) |

### `product`

Product taxonomy: 12 fictional products in 4 categories.

- **Primary key:** product_id
- **Effective dates:** launched_at (all launched before the feedback window).
- **Lifecycle:** ACTIVE -> RETIRED (all ACTIVE in this dataset)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| product_id | id | yes |  |  | yes |  | PROD-0001 |
| name | str | yes |  |  | yes |  |  |
| category | enum | yes | mobile_app, subscription_plan, smart_device, delivery_service |  |  |  | decides which themes are applicable (taxonomy.APPLICABLE_THEMES) |
| launched_at | date | yes |  |  |  |  | < 2026-04-06 |
| status | enum | yes | ACTIVE, RETIRED |  |  |  |  |

### `channel`

Channel taxonomy: where feedback arrives.

- **Primary key:** channel_id
- **Effective dates:** static
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| channel_id | id | yes |  |  | yes |  | CHAN-01..CHAN-06 |
| name | enum | yes | web_survey, email_survey, app_store, website_review, chat, email_support |  | yes |  |  |
| channel_type | enum | yes | survey, review, support |  |  |  | survey channels only on surveys, review channels only on reviews, support only on tickets |

### `survey`

A survey campaign; general (no product) or product-specific.

- **Primary key:** survey_id
- **Effective dates:** opens_at <= closes_at; responses only inside [opens_at, closes_at].
- **Lifecycle:** DRAFT -> OPEN -> CLOSED; DERIVED from dates vs reference date 2026-10-01
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| survey_id | id | yes |  |  | yes |  | SUR-2026-000001, ordered by opens_at |
| name | str | yes |  |  |  |  |  |
| channel_id | id | yes |  |  |  | channel.channel_id | channel_type = survey |
| product_id | id | no |  |  |  | product.product_id | null = general survey |
| opens_at | date | yes |  |  |  |  |  |
| closes_at | date | yes |  |  |  |  | >= opens_at |
| status | enum | yes | DRAFT, OPEN, CLOSED |  |  |  | DRAFT if opens_at > ref; CLOSED if closes_at < ref; else OPEN |

### `theme`

Theme taxonomy: 10 top-level themes + 2 child themes (late_delivery under delivery, double_charge under billing).

- **Primary key:** theme_id
- **Effective dates:** effective_from (2026-01-01); effective_to null = current version.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| theme_id | id | yes |  |  | yes |  | THEME-000001 |
| code | str | yes |  |  | yes |  | snake_case |
| name | str | yes |  |  |  |  |  |
| parent_theme_id | id | no |  |  |  | theme.theme_id | one level deep; parent must be top-level |
| keywords | str | yes |  |  |  |  | '|'-separated cue words (documentation / analysis hints) |
| severity_weight | int | yes | 1, 2, 3 | weight |  |  | used in the priority score |
| effective_from | date | yes |  |  |  |  |  |
| effective_to | date | no |  |  |  |  | null or > effective_from |

## Feedback (children)

### `survey_response`

One customer's answer to a survey: NPS-style score + free text.

- **Primary key:** response_id
- **Effective dates:** submitted_at within the survey window and within 2026-04-06..2026-09-27.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| response_id | id | yes |  |  | yes |  | RESP-<survey_id>-NNN e.g. RESP-SUR-2026-000001-001; counter per survey |
| survey_id | id | yes |  |  |  | survey.survey_id | survey.status != DRAFT |
| customer_id | id | yes |  |  |  | customer.customer_id | one response per (customer, survey) except planted DUPLICATE_RESPONSE |
| product_id | id | yes |  |  |  | product.product_id | = survey.product_id when the survey has one |
| score | int | yes | 0..10 | 0-10 NPS points |  |  | derived range from text sentiment: pos 9-10, neg 0-6, neu 7-8, mixed 5-8 |
| text | text | yes |  |  |  |  | synthetic, template-generated |
| language | enum | yes | en, es, hi, te, hi-Latn |  |  |  | = customer.preferred_language |
| submitted_at | datetime | yes |  |  |  |  |  |
| tags | str | no |  |  |  |  | ';'-separated source tags: verified_purchase|promo|beta_user |

### `review`

A product review from an app store or the website.

- **Primary key:** review_id
- **Effective dates:** posted_at within 2026-04-06..2026-09-27.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| review_id | id | yes |  |  | yes |  | REV-2026-000001, ordered by posted_at |
| customer_id | id | yes |  |  |  | customer.customer_id |  |
| product_id | id | yes |  |  |  | product.product_id |  |
| channel_id | id | yes |  |  |  | channel.channel_id | channel_type = review |
| rating | int | yes | 1, 2, 3, 4, 5 | stars |  |  | derived range from text sentiment: pos 4-5, neg 1-2, neu 3, mixed 2-4 |
| text | text | yes |  |  |  |  |  |
| language | enum | yes | en, es, hi, te, hi-Latn |  |  |  | = customer.preferred_language |
| posted_at | datetime | yes |  |  |  |  |  |
| tags | str | no |  |  |  |  | ';'-separated source tags |

### `support_ticket`

A support case. Status and closed_at are DERIVED from ticket_status_event.

- **Primary key:** ticket_id
- **Effective dates:** opened_at <= every message/event <= closed_at (if closed); all < 2026-10-01.
- **Lifecycle:** OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED; RESOLVED -> REOPENED -> IN_PROGRESS
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| ticket_id | id | yes |  |  | yes |  | TKT-2026-000001, ordered by opened_at |
| customer_id | id | yes |  |  |  | customer.customer_id |  |
| product_id | id | yes |  |  |  | product.product_id |  |
| channel_id | id | yes |  |  |  | channel.channel_id | channel_type = support |
| opened_at | datetime | yes |  |  |  |  |  |
| closed_at | datetime | no |  |  |  |  | = event_at of the CLOSED event; null if not closed |
| current_status | enum | yes | OPEN, IN_PROGRESS, RESOLVED, REOPENED, CLOSED |  |  |  | = to_status of the latest event |

### `support_message`

A message in a ticket thread. Customer messages are feedback; agent messages are not labelled.

- **Primary key:** message_id
- **Effective dates:** sent_at ascending within a ticket, >= ticket.opened_at.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| message_id | id | yes |  |  | yes |  | MSG-<ticket_id>-NNN e.g. MSG-TKT-2026-000001-001; counter per ticket |
| ticket_id | id | yes |  |  |  | support_ticket.ticket_id |  |
| sender | enum | yes | customer, agent |  |  |  | alternates, first is customer |
| text | text | yes |  |  |  |  |  |
| language | enum | yes | en, es, hi, te, hi-Latn |  |  |  | customer: preferred_language; agent: en |
| sent_at | datetime | yes |  |  |  |  |  |

## Event history (append-only)

### `ticket_status_event`

Append-only ticket status history (never updated or deleted).

- **Primary key:** event_id
- **Effective dates:** event_at ascending per ticket.
- **Lifecycle:** see support_ticket
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| event_id | id | yes |  |  | yes |  | TSE-000001 |
| ticket_id | id | yes |  |  |  | support_ticket.ticket_id |  |
| from_status | enum | no | OPEN, IN_PROGRESS, RESOLVED, REOPENED, CLOSED |  |  |  | null only for the first (OPEN) event |
| to_status | enum | yes | OPEN, IN_PROGRESS, RESOLVED, REOPENED, CLOSED |  |  |  | (from,to) must be a legal transition |
| actor | enum | yes | customer, agent, system |  |  |  |  |
| event_at | datetime | yes |  |  |  |  |  |

## Labels and bridge tables (input)

### `sentiment_label`

Sentiment label on a feedback item. Generator writes source-system tags for ~30% of TRAIN items only; analysis adds labeler=model rows; human review is logged in label_review_event.

- **Primary key:** label_id
- **Effective dates:** labeled_at after the feedback timestamp.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| label_id | id | yes |  |  | yes |  | LBL-000001 |
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  | polymorphic FK -> review / survey_response / support_message (validated in code) |
| sentiment | enum | yes | positive, negative, neutral, mixed |  |  |  |  |
| labeler | enum | yes | source_system, model, human |  |  |  |  |
| label_note | str | no |  |  |  |  | free-text justification |
| labeled_at | datetime | yes |  |  |  |  |  |

### `feedback_theme`

Bridge table feedback N:M theme (a mixed text has 2 themes).

- **Primary key:** source_type, source_id, theme_id, labeler
- **Effective dates:** tagged_at.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  | polymorphic FK, as in sentiment_label |
| theme_id | id | yes |  |  |  | theme.theme_id | must exist in taxonomy (planted THEME_OUTSIDE_TAXONOMY violates it) |
| labeler | enum | yes | source_system, model, human |  |  |  |  |
| tagged_at | datetime | yes |  |  |  |  |  |

## Created later by analysis / validation

### `action_item`

Prioritised action created by the analysis rule from a recurring negative theme x product.

- **Primary key:** action_item_id
- **Effective dates:** created_at <= updated_at.
- **Lifecycle:** OPEN -> IN_PROGRESS -> DONE | DISMISSED (history in action_item_event)
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| action_item_id | id | yes |  |  | yes |  | ACT-000001 |
| theme_id | id | yes |  |  |  | theme.theme_id |  |
| product_id | id | yes |  |  |  | product.product_id |  |
| priority_score | float | yes |  | score |  |  | DERIVED = volume x negative_share x severity_weight x (1 + shift) |
| status | enum | yes | OPEN, IN_PROGRESS, DONE, DISMISSED |  |  |  | = to_status of the latest action_item_event |
| owner_role | enum | yes | support_lead, product_manager, billing_ops, logistics_ops |  |  |  |  |
| evidence_count | int | yes |  | records |  |  | DERIVED = number of evidence_ids |
| evidence_ids | str | yes |  |  |  |  | '|'-separated source ids (traceability) |
| created_from_rule | str | yes |  |  |  |  | rule id + parameters that fired |
| created_at | datetime | yes |  |  |  |  |  |
| updated_at | datetime | yes |  |  |  |  |  |

### `action_item_event`

Append-only status history of action items.

- **Primary key:** event_id
- **Effective dates:** event_at.
- **Lifecycle:** see action_item
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| event_id | id | yes |  |  | yes |  | AIE-000001 |
| action_item_id | id | yes |  |  |  | action_item.action_item_id |  |
| from_status | enum | no | OPEN, IN_PROGRESS, DONE, DISMISSED |  |  |  |  |
| to_status | enum | yes | OPEN, IN_PROGRESS, DONE, DISMISSED |  |  |  |  |
| actor | str | yes |  |  |  |  |  |
| note | str | no |  |  |  |  |  |
| event_at | datetime | yes |  |  |  |  |  |

### `label_review_event`

Append-only human review of eval-set labels (confirm / override).

- **Primary key:** event_id
- **Effective dates:** event_at.
- **Lifecycle:** none (immutable record)
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| event_id | id | yes |  |  | yes |  | LRE-000001 |
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  |  |
| old_sentiment | enum | yes | positive, negative, neutral, mixed |  |  |  |  |
| new_sentiment | enum | yes | positive, negative, neutral, mixed |  |  |  |  |
| old_theme_ids | str | yes |  |  |  |  |  |
| new_theme_ids | str | yes |  |  |  |  |  |
| decision | enum | yes | confirmed, overridden |  |  |  |  |
| reviewer | str | yes |  |  |  |  |  |
| event_at | datetime | yes |  |  |  |  |  |

### `data_exception`

Exception path: every failed check / detected anomaly becomes a row; nothing crashes.

- **Primary key:** exception_id
- **Effective dates:** detected_at.
- **Lifecycle:** OPEN -> RESOLVED | ACCEPTED
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| exception_id | id | yes |  |  | yes |  | EXC-000001 |
| table_name | str | yes |  |  |  |  | table the offending row lives in |
| record_key | str | yes |  |  |  |  | PK of the offending row ('|'-joined if composite) |
| source_type | enum | no | review, survey_response, support_message |  |  |  | feedback item the row is about (null for master data) |
| source_id | id | no |  |  |  |  | polymorphic, as in sentiment_label |
| exception_type | str | yes |  |  |  |  | validation check name or one of the 5 issue types |
| check_name | str | yes |  |  |  |  | the check that raised it (validate/checks.py or analysis rule id) |
| check_category | enum | yes | validity, integrity, temporal, reconciliation, lifecycle, duplicate, leakage, privacy, label_quality |  |  |  |  |
| disposition | enum | yes | QUARANTINE, FLAG |  |  |  | QUARANTINE = row kept in DB but excluded from analysis; FLAG = kept and shown on data-quality page |
| detail | str | yes |  |  |  |  | expected vs actual |
| detected_by | enum | yes | validation, analysis |  |  |  |  |
| detected_at | datetime | yes |  |  |  |  |  |
| resolution_status | enum | yes | OPEN, RESOLVED, ACCEPTED |  |  |  |  |

### `pipeline_run`

One execution of the analysis stages; parameters and lexicon hash make every prediction reproducible.

- **Primary key:** run_id
- **Effective dates:** started_at <= finished_at.
- **Lifecycle:** SUCCEEDED | FAILED (append-only)
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| run_id | id | yes |  |  | yes |  | RUN-000001 |
| stage | str | yes |  |  |  |  | e.g. analyze |
| params | str | yes |  |  |  |  | JSON: tau, rule settings |
| lexicon_hash | str | yes |  |  |  |  | SHA-256 (12 chars) of analyze/lexicon.py |
| n_items | int | yes |  | records |  |  |  |
| n_auto | int | yes |  | records |  |  |  |
| n_review | int | yes |  | records |  |  |  |
| status | enum | yes | SUCCEEDED, FAILED |  |  |  |  |
| started_at | datetime | yes |  |  |  |  |  |
| finished_at | datetime | yes |  |  |  |  |  |

### `feedback_item`

Curated, unified feedback (reviews + survey responses + customer support messages), PII-redacted. Quarantined rows excluded.

- **Primary key:** source_type, source_id
- **Effective dates:** event_at; week_start = Monday of the ISO week.
- **Lifecycle:** none (immutable record)
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  |  |
| customer_id | id | yes |  |  |  | customer.customer_id |  |
| product_id | id | yes |  |  |  | product.product_id |  |
| channel_id | id | yes |  |  |  | channel.channel_id |  |
| channel_type | enum | yes | survey, review, support |  |  |  |  |
| event_at | datetime | yes |  |  |  |  |  |
| week_start | date | yes |  |  |  |  | Monday of event_at's ISO week |
| score_norm | float | no |  | 0-1 |  |  | DERIVED: (rating-1)/4 or score/10; null for messages |
| language | enum | yes | en, es, hi, te, hi-Latn |  |  |  | declared by the source |
| language_detected | enum | yes | en, es, hi, te, hi-Latn |  |  |  | script + marker words |
| code_mixed | int | yes | 0, 1 |  |  |  | 1 if Latin-script Hindi/English mix |
| redacted_text | text | yes |  |  |  |  | emails, phones, known customer names replaced by [EMAIL]/[PHONE]/[NAME] |
| pii_count | int | yes |  | redactions |  |  |  |
| run_id | id | yes |  |  |  | pipeline_run.run_id |  |

### `prediction`

Explainable sentiment + theme prediction per feedback item, with confidence, evidence, rules and routing.

- **Primary key:** source_type, source_id
- **Effective dates:** valid for run_id.
- **Lifecycle:** auto | review (human decision in label_review_event)
- **Produced by:** analysis / validation pipeline

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  |  |
| sentiment | enum | yes | positive, negative, neutral, mixed |  |  |  |  |
| confidence | float | yes |  | 0-1 |  |  | rule-based certainty of the sentiment |
| theme_ids | str | no |  |  |  |  | '|'-separated, most specific theme; null = unclassified |
| evidence | str | no |  |  |  |  | '|'-separated matched cues, e.g. +recommend|-never arrives |
| rules_fired | str | yes |  |  |  |  | '|'-separated rule ids, e.g. LEX|NEGATION|CONTRAST |
| route | enum | yes | auto, review |  |  |  | review if confidence < tau or a risk rule fired |
| route_reason | str | no |  |  |  |  |  |
| run_id | id | yes |  |  |  | pipeline_run.run_id |  |

## Ground truth - evaluation only (data/output/ground_truth/)

### `gt_labels` -> `labels.csv`

Gold labels for EVERY labelled feedback item, decided by the template that produced the text.

- **Primary key:** source_type, source_id
- **Effective dates:** -
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  |  |
| sentiment | enum | yes | positive, negative, neutral, mixed |  |  |  |  |
| theme_ids | str | yes |  |  |  |  | '|'-separated THEME ids, most specific theme |
| style | enum | yes | plain, mixed, sarcastic, negation, ambiguous, multilingual |  |  |  |  |
| language | enum | yes | en, es, hi, te, hi-Latn |  |  |  |  |
| template_id | str | yes |  |  |  |  | frame id, e.g. EN-SARCASTIC-NEG-02 / TE-MIX-01 |
| incident_id | id | no |  |  |  |  | incident that caused this item |
| incident_phase | enum | no | pre, post |  |  |  |  |
| product_id | id | yes |  |  |  |  |  |
| split | enum | yes | train, eval |  |  |  | eval stratified by sentiment |

### `gt_incidents` -> `incidents.csv`

Hidden incidents that cause sentiment shifts, with explicit per-channel lag (support 0, review +3, survey +7 days).

- **Primary key:** incident_id
- **Effective dates:** onset_date..end_date; <channel>_signal_start = onset + lag.
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| incident_id | id | yes |  |  |  |  |  |
| name | str | yes |  |  |  |  |  |
| description | str | yes |  |  |  |  |  |
| product_id | id | yes |  |  |  |  |  |
| direction | enum | yes | worsen, improve |  |  |  |  |
| theme_id | id | yes |  |  |  |  |  |
| onset_date | date | yes |  |  |  |  |  |
| end_date | date | yes |  |  |  |  |  |
| lag_support_days | int | yes |  | days |  |  |  |
| support_signal_start | date | yes |  |  |  |  |  |
| lag_review_days | int | yes |  | days |  |  |  |
| review_signal_start | date | yes |  |  |  |  |  |
| lag_survey_days | int | yes |  | days |  |  |  |
| survey_signal_start | date | yes |  |  |  |  |  |
| volume_boost | float | yes |  | x extra weight |  |  |  |
| override_prob | float | yes |  | probability |  |  |  |
| pre_onset_prob | float | yes |  | probability |  |  |  |
| n_support_items | int | yes |  | records |  |  | DERIVED count of caused items |
| n_review_items | int | yes |  | records |  |  |  |
| n_survey_items | int | yes |  | records |  |  |  |

### `gt_anomalies` -> `anomalies.csv`

The 5 planted edge-case types with the decision the pipeline is expected to take.

- **Primary key:** anomaly_id
- **Effective dates:** -
- **Lifecycle:** none (immutable record)
- **Produced by:** generator

| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |
|---|---|---|---|---|---|---|---|
| anomaly_id | id | yes |  |  | yes |  | ANOM-0001 |
| issue_type | enum | yes | LABEL_CONTRADICTS_TEXT, DUPLICATE_RESPONSE, PII_LEAK, THEME_OUTSIDE_TAXONOMY, TEST_LABEL_IN_MODEL_INPUT |  |  |  |  |
| source_type | enum | yes | review, survey_response, support_message |  |  |  |  |
| source_id | id | yes |  |  |  |  |  |
| detail | str | yes |  |  |  |  |  |
| expected_decision | str | yes |  |  |  |  |  |

## ID formats

| Field | Pattern |
|---|---|
| customer_id | `^CUST-\d{6}$` |
| product_id | `^PROD-\d{4}$` |
| channel_id | `^CHAN-\d{2}$` |
| survey_id | `^SUR-2026-\d{6}$` |
| theme_id | `^THEME-\d{6}$` |
| response_id | `^RESP-SUR-2026-\d{6}-\d{3}$` |
| review_id | `^REV-2026-\d{6}$` |
| ticket_id | `^TKT-2026-\d{6}$` |
| message_id | `^MSG-TKT-2026-\d{6}-\d{3}$` |
| label_id | `^LBL-\d{6}$` |
| event_id | `^(TSE|AIE|LRE)-\d{6}$` |
| action_item_id | `^ACT-\d{6}$` |
| exception_id | `^EXC-\d{6}$` |
| run_id | `^RUN-\d{6}$` |
| incident_id | `^INC-\d{2}$` |
| anomaly_id | `^ANOM-\d{4}$` |
