Hackathon Round
Submit Your Hackathon Work
Associate AI Forward Deployed Engineers · AI Forward Deployed Engineer

Problem statement
Read it carefully. Your build should cover every point below.

Business Context / Problem
Combine survey responses, reviews and support text to identify recurring themes, sentiment shifts and service priorities.

Objective and Scope
Build a working solution for this end-to-end workflow: Combine survey responses, reviews and support text to identify recurring themes, sentiment shifts and service priorities. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.

Primary Actors / Systems
Customer/prospect, marketing/sales operations, support agent, analyst and system administrator

Business Workflow and Rules
1. Generate/reference master data first: Customer, Product, Channel, Survey, SurveyResponse.
2. Generate dependent transaction/event records using valid parent IDs.
3. Apply business logic: Create product/channel taxonomy; generate synthetic review and ticket text with balanced sentiment/theme labels; link responses to dates/products; include neutral, mixed and multilingual examples; define theme taxonomy; create action items from recurring themes.
4. Persist state changes as explicit records/events where relevant; do not overwrite history.
5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.

Entities and Relationships
Core entities: Customer, Product, Channel, Survey, SurveyResponse, Review, SupportMessage, Theme, SentimentLabel, ActionItem. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.

ID / Nomenclature Conventions
SUR-2026-000001; RESP-<survey-id>-001; REV-2026-000001; MSG-<ticket-id>-001; THEME-000001.

Synthetic Data Generation Instructions (Granular)
Step 1 — Write a data dictionary for: Customer, Product, Channel, Survey, SurveyResponse, Review, SupportMessage, Theme, SentimentLabel, ActionItem. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule.
Step 2 — Create parent/master tables first, then child and event tables. Apply this domain-specific generation logic: Create product/channel taxonomy; generate synthetic review and ticket text with balanced sentiment/theme labels; link responses to dates/products; include neutral, mixed and multilingual examples; define theme taxonomy; create action items from recurring themes.
Step 3 — Apply deterministic IDs and naming: SUR-2026-000001; RESP-<survey-id>-001; REV-2026-000001; MSG-<ticket-id>-001; THEME-000001. Keep counters zero-padded, IDs immutable, and referenced IDs exactly consistent across files.
Step 4 — Generate the baseline volume: Generate 50,000 reviews/responses and 20,000 support messages. Ensure label balance, realistic language variation, sarcasm and ambiguous examples; keep text synthetic or properly licensed. Use a fixed seed (e.g. 20261022) and parameterize scale so starter and full datasets use the same generator.
Step 5 — Generate valid baseline records first, then inject labelled edge cases: Label contradicts text without explanation; duplicate response; customer identity leaked; theme assigned outside taxonomy; test labels included in model input.
Step 6 — Calculate derived values (totals, balances, scores, statuses and dates) from source records rather than generating them independently.
Step 7 — Produce a separate ground_truth.csv/json for known anomalies, expected decisions or labels; never leak it into input features.
Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks.
Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary.
Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.

Suggested Volume and Coverage
Generate 50,000 reviews/responses and 20,000 support messages. Ensure label balance, realistic language variation, sarcasm and ambiguous examples; keep text synthetic or properly licensed.

Required Edge Cases / Negative Scenarios
Label contradicts text without explanation; duplicate response; customer identity leaked; theme assigned outside taxonomy; test labels included in model input.

Validation Rules / Acceptance Criteria
Evaluation set has human-reviewed labels; sentiment/theme metrics are measurable; privacy-safe synthetic text is used; trends can be traced to source records.

Evaluation Focus for Generated Data
Review: (a) realistic distributions and meaningful variation; (b) consistent IDs and valid joins; (c) dependency/lifecycle consistency across entities; (d) correct derived values and reconciliation; (e) normal, boundary, failure and exception coverage; (f) separate ground truth; (g) fixed-seed reproducibility, documentation and lawful provenance.

Public Data Guidance / Lawful Use
External data is optional. If used, record source URL, dataset/version, retrieval date, license/terms, attribution, transformations and fields discarded. Use only data you are legally permitted to access and redistribute; do not bypass access controls or collect confidential/personal information. If licensing or suitability is unclear, use synthetic data and cite public reference data only for schema inspiration.