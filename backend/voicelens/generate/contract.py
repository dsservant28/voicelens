"""The data contract: ONE definition of every entity, used to
  (1) render docs/DATA_DICTIONARY.md   (python -m voicelens.generate.contract)
  (2) emit the SQL DDL in the seed file (export.py)
  (3) drive the Step-2 validator (types, required, enums, uniqueness, FKs, lifecycles).
Docs and checks therefore cannot drift apart.
"""
from __future__ import annotations

import sys
from pathlib import Path

LANG = ["en", "es", "hi", "te", "hi-Latn"]
SENT = ["positive", "negative", "neutral", "mixed"]
SOURCE_TYPES = ["review", "survey_response", "support_message"]
TICKET_STATUS = ["OPEN", "IN_PROGRESS", "RESOLVED", "REOPENED", "CLOSED"]
ACTION_STATUS = ["OPEN", "IN_PROGRESS", "DONE", "DISMISSED"]
ISSUE_TYPES = ["LABEL_CONTRADICTS_TEXT", "DUPLICATE_RESPONSE", "PII_LEAK", "THEME_OUTSIDE_TAXONOMY",
               "TEST_LABEL_IN_MODEL_INPUT"]
STYLES = ["plain", "mixed", "sarcastic", "negation", "ambiguous", "multilingual"]
SOURCE_TAGS = ["verified_purchase", "promo", "beta_user"]          # allowed values inside `tags` (';'-separated)
# Legal (from_status, to_status) pairs; None = first event. Used by the validator's lifecycle check.
TRANSITIONS = {
    "ticket_status_event": {(None, "OPEN"), ("OPEN", "IN_PROGRESS"), ("IN_PROGRESS", "RESOLVED"),
                            ("RESOLVED", "CLOSED"), ("RESOLVED", "REOPENED"), ("REOPENED", "IN_PROGRESS")},
    "action_item_event": {(None, "OPEN"), ("OPEN", "IN_PROGRESS"), ("OPEN", "DISMISSED"), ("IN_PROGRESS", "DONE"),
                          ("IN_PROGRESS", "DISMISSED")},
}

ID_PATTERNS = {
    "customer_id": r"^CUST-\d{6}$", "product_id": r"^PROD-\d{4}$", "channel_id": r"^CHAN-\d{2}$",
    "survey_id": r"^SUR-2026-\d{6}$", "theme_id": r"^THEME-\d{6}$",
    "response_id": r"^RESP-SUR-2026-\d{6}-\d{3}$", "review_id": r"^REV-2026-\d{6}$",
    "ticket_id": r"^TKT-2026-\d{6}$", "message_id": r"^MSG-TKT-2026-\d{6}-\d{3}$",
    "label_id": r"^LBL-\d{6}$", "event_id": r"^(TSE|AIE|LRE)-\d{6}$", "action_item_id": r"^ACT-\d{6}$",
    "exception_id": r"^EXC-\d{6}$", "run_id": r"^RUN-\d{6}$", "alert_id": r"^ALR-\d{6}$",
    "cell_id": r"^CELL-\d{4}-\d{2}-\d{2}-PROD-\d{4}-THEME-\d{6}-(survey|review|support)$", "incident_id": r"^INC-\d{2}$", "anomaly_id": r"^ANOM-\d{4}$",
}


def f(name, type_, req=True, allowed=None, unit="", unique=False, rule="", fk=None):
    return {"name": name, "type": type_, "required": req, "allowed": allowed, "unit": unit,
            "unique": unique, "rule": rule, "fk": fk}


def rel(field, parent, cardinality, optional=False, note=""):
    return {"field": field, "parent": parent, "cardinality": cardinality, "optional": optional, "note": note}


ENTITIES: dict[str, dict] = {
    # ------------------------------------------------------------------ master data
    "customer": {
        "group": "master", "pk": ["customer_id"], "generated": True,
        "description": "A customer/prospect who gives feedback. Synthetic identity (fake name, example.com email, 555-01xx phone).",
        "effective_dates": "created_at (account creation; always before any of the customer's feedback).",
        "lifecycle": None,
        "fields": [
            f("customer_id", "id", unique=True, rule="CUST-000001, zero-padded, immutable"),
            f("display_name", "str", rule="synthetic 'First Last'; PII - must be redacted if it appears in text"),
            f("email", "str", unique=True, rule="<first>.<last><n>@example.com (reserved domain); PII"),
            f("phone", "str", rule="+1-555-01NN fictional range; not unique; PII"),
            f("segment", "enum", allowed=["consumer", "smb", "enterprise"]),
            f("region", "enum", allowed=["IN-North", "IN-South", "IN-East", "IN-West", "International"]),
            f("preferred_language", "enum", allowed=LANG, rule="the language the customer writes feedback in"),
            f("created_at", "date", rule="2024-01-01 <= created_at < 2026-04-06 (window start)"),
        ],
        "relationships": [],
    },
    "product": {
        "group": "master", "pk": ["product_id"], "generated": True,
        "description": "Product taxonomy: 12 fictional products in 4 categories.",
        "effective_dates": "launched_at (all launched before the feedback window).",
        "lifecycle": "ACTIVE -> RETIRED (all ACTIVE in this dataset)",
        "fields": [
            f("product_id", "id", unique=True, rule="PROD-0001"),
            f("name", "str", unique=True),
            f("category", "enum", allowed=["mobile_app", "subscription_plan", "smart_device", "delivery_service"],
              rule="decides which themes are applicable (taxonomy.APPLICABLE_THEMES)"),
            f("launched_at", "date", rule="< 2026-04-06"),
            f("status", "enum", allowed=["ACTIVE", "RETIRED"]),
        ],
        "relationships": [],
    },
    "channel": {
        "group": "master", "pk": ["channel_id"], "generated": True,
        "description": "Channel taxonomy: where feedback arrives.",
        "effective_dates": "static", "lifecycle": None,
        "fields": [
            f("channel_id", "id", unique=True, rule="CHAN-01..CHAN-06"),
            f("name", "enum", unique=True, allowed=["web_survey", "email_survey", "app_store", "website_review",
                                                    "chat", "email_support"]),
            f("channel_type", "enum", allowed=["survey", "review", "support"],
              rule="survey channels only on surveys, review channels only on reviews, support only on tickets"),
        ],
        "relationships": [],
    },
    "survey": {
        "group": "master", "pk": ["survey_id"], "generated": True,
        "description": "A survey campaign; general (no product) or product-specific.",
        "effective_dates": "opens_at <= closes_at; responses only inside [opens_at, closes_at].",
        "lifecycle": "DRAFT -> OPEN -> CLOSED; DERIVED from dates vs reference date 2026-10-01",
        "fields": [
            f("survey_id", "id", unique=True, rule="SUR-2026-000001, ordered by opens_at"),
            f("name", "str"),
            f("channel_id", "id", fk="channel.channel_id", rule="channel_type = survey"),
            f("product_id", "id", req=False, fk="product.product_id", rule="null = general survey"),
            f("opens_at", "date"),
            f("closes_at", "date", rule=">= opens_at"),
            f("status", "enum", allowed=["DRAFT", "OPEN", "CLOSED"],
              rule="DRAFT if opens_at > ref; CLOSED if closes_at < ref; else OPEN"),
        ],
        "relationships": [rel("channel_id", "channel", "N:1"), rel("product_id", "product", "N:1", optional=True)],
    },
    "theme": {
        "group": "master", "pk": ["theme_id"], "generated": True,
        "description": "Theme taxonomy: 10 top-level themes + 2 child themes (late_delivery under delivery, double_charge under billing).",
        "effective_dates": "effective_from (2026-01-01); effective_to null = current version.",
        "lifecycle": None,
        "fields": [
            f("theme_id", "id", unique=True, rule="THEME-000001"),
            f("code", "str", unique=True, rule="snake_case"),
            f("name", "str"),
            f("parent_theme_id", "id", req=False, fk="theme.theme_id", rule="one level deep; parent must be top-level"),
            f("keywords", "str", rule="'|'-separated cue words (documentation / analysis hints)"),
            f("severity_weight", "int", allowed=[1, 2, 3], unit="weight", rule="used in the priority score"),
            f("effective_from", "date"),
            f("effective_to", "date", req=False, rule="null or > effective_from"),
        ],
        "relationships": [rel("parent_theme_id", "theme", "N:1 (self)", optional=True)],
    },
    # ------------------------------------------------------------------ feedback
    "survey_response": {
        "group": "feedback", "pk": ["response_id"], "generated": True,
        "description": "One customer's answer to a survey: NPS-style score + free text.",
        "effective_dates": "submitted_at within the survey window and within 2026-04-06..2026-09-27.",
        "lifecycle": None,
        "fields": [
            f("response_id", "id", unique=True, rule="RESP-<survey_id>-NNN e.g. RESP-SUR-2026-000001-001; counter per survey"),
            f("survey_id", "id", fk="survey.survey_id", rule="survey.status != DRAFT"),
            f("customer_id", "id", fk="customer.customer_id", rule="one response per (customer, survey) except planted DUPLICATE_RESPONSE"),
            f("product_id", "id", fk="product.product_id", rule="= survey.product_id when the survey has one"),
            f("score", "int", allowed=list(range(11)), unit="0-10 NPS points",
              rule="derived range from text sentiment: pos 9-10, neg 0-6, neu 7-8, mixed 5-8"),
            f("text", "text", rule="synthetic, template-generated"),
            f("language", "enum", allowed=LANG, rule="= customer.preferred_language"),
            f("submitted_at", "datetime"),
            f("tags", "str", req=False, rule="';'-separated source tags: verified_purchase|promo|beta_user"),
        ],
        "relationships": [rel("survey_id", "survey", "N:1"), rel("customer_id", "customer", "N:1"),
                          rel("product_id", "product", "N:1")],
    },
    "review": {
        "group": "feedback", "pk": ["review_id"], "generated": True,
        "description": "A product review from an app store or the website.",
        "effective_dates": "posted_at within 2026-04-06..2026-09-27.", "lifecycle": None,
        "fields": [
            f("review_id", "id", unique=True, rule="REV-2026-000001, ordered by posted_at"),
            f("customer_id", "id", fk="customer.customer_id"),
            f("product_id", "id", fk="product.product_id"),
            f("channel_id", "id", fk="channel.channel_id", rule="channel_type = review"),
            f("rating", "int", allowed=[1, 2, 3, 4, 5], unit="stars",
              rule="derived range from text sentiment: pos 4-5, neg 1-2, neu 3, mixed 2-4"),
            f("text", "text"),
            f("language", "enum", allowed=LANG, rule="= customer.preferred_language"),
            f("posted_at", "datetime"),
            f("tags", "str", req=False, rule="';'-separated source tags"),
        ],
        "relationships": [rel("customer_id", "customer", "N:1"), rel("product_id", "product", "N:1"),
                          rel("channel_id", "channel", "N:1")],
    },
    "support_ticket": {
        "group": "feedback", "pk": ["ticket_id"], "generated": True,
        "description": "A support case. Status and closed_at are DERIVED from ticket_status_event.",
        "effective_dates": "opened_at <= every message/event <= closed_at (if closed); all < 2026-10-01.",
        "lifecycle": "OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED; RESOLVED -> REOPENED -> IN_PROGRESS",
        "fields": [
            f("ticket_id", "id", unique=True, rule="TKT-2026-000001, ordered by opened_at"),
            f("customer_id", "id", fk="customer.customer_id"),
            f("product_id", "id", fk="product.product_id"),
            f("channel_id", "id", fk="channel.channel_id", rule="channel_type = support"),
            f("opened_at", "datetime"),
            f("closed_at", "datetime", req=False, rule="= event_at of the CLOSED event; null if not closed"),
            f("current_status", "enum", allowed=TICKET_STATUS, rule="= to_status of the latest event"),
        ],
        "relationships": [rel("customer_id", "customer", "N:1"), rel("product_id", "product", "N:1"),
                          rel("channel_id", "channel", "N:1")],
    },
    "support_message": {
        "group": "feedback", "pk": ["message_id"], "generated": True,
        "description": "A message in a ticket thread. Customer messages are feedback; agent messages are not labelled.",
        "effective_dates": "sent_at ascending within a ticket, >= ticket.opened_at.", "lifecycle": None,
        "fields": [
            f("message_id", "id", unique=True, rule="MSG-<ticket_id>-NNN e.g. MSG-TKT-2026-000001-001; counter per ticket"),
            f("ticket_id", "id", fk="support_ticket.ticket_id"),
            f("sender", "enum", allowed=["customer", "agent"], rule="alternates, first is customer"),
            f("text", "text"),
            f("language", "enum", allowed=LANG, rule="customer: preferred_language; agent: en"),
            f("sent_at", "datetime"),
        ],
        "relationships": [rel("ticket_id", "support_ticket", "N:1")],
    },
    "ticket_status_event": {
        "group": "events", "pk": ["event_id"], "generated": True,
        "description": "Append-only ticket status history (never updated or deleted).",
        "effective_dates": "event_at ascending per ticket.", "lifecycle": "see support_ticket",
        "fields": [
            f("event_id", "id", unique=True, rule="TSE-000001"),
            f("ticket_id", "id", fk="support_ticket.ticket_id"),
            f("from_status", "enum", req=False, allowed=TICKET_STATUS, rule="null only for the first (OPEN) event"),
            f("to_status", "enum", allowed=TICKET_STATUS, rule="(from,to) must be a legal transition"),
            f("actor", "enum", allowed=["customer", "agent", "system"]),
            f("event_at", "datetime"),
        ],
        "relationships": [rel("ticket_id", "support_ticket", "N:1")],
    },
    # ------------------------------------------------------------------ labels / bridge (input tags)
    "sentiment_label": {
        "group": "labels", "pk": ["label_id"], "generated": True,
        "description": "Sentiment label on a feedback item. Generator writes source-system tags for ~30% of TRAIN items only; analysis adds labeler=model rows; human review is logged in label_review_event.",
        "effective_dates": "labeled_at after the feedback timestamp.", "lifecycle": None,
        "fields": [
            f("label_id", "id", unique=True, rule="LBL-000001"),
            f("source_type", "enum", allowed=SOURCE_TYPES),
            f("source_id", "id", rule="polymorphic FK -> review / survey_response / support_message (validated in code)"),
            f("sentiment", "enum", allowed=SENT),
            f("labeler", "enum", allowed=["source_system", "model", "human"]),
            f("label_note", "str", req=False, rule="free-text justification"),
            f("labeled_at", "datetime"),
        ],
        "relationships": [rel("source_id", "review / survey_response / support_message", "N:1", note="polymorphic via source_type")],
    },
    "feedback_theme": {
        "group": "labels", "pk": ["source_type", "source_id", "theme_id", "labeler"], "generated": True,
        "description": "Bridge table feedback N:M theme (a mixed text has 2 themes).",
        "effective_dates": "tagged_at.", "lifecycle": None,
        "fields": [
            f("source_type", "enum", allowed=SOURCE_TYPES),
            f("source_id", "id", rule="polymorphic FK, as in sentiment_label"),
            f("theme_id", "id", fk="theme.theme_id", rule="must exist in taxonomy (planted THEME_OUTSIDE_TAXONOMY violates it)"),
            f("labeler", "enum", allowed=["source_system", "model", "human"]),
            f("tagged_at", "datetime"),
        ],
        "relationships": [rel("theme_id", "theme", "N:1"),
                          rel("source_id", "review / survey_response / support_message", "N:1", note="feedback N:M theme")],
    },
    # ------------------------------------------------------------------ created later by analysis / validation
    "action_item": {
        "group": "downstream", "pk": ["action_item_id"], "generated": False,
        "description": "Prioritised action created by the analysis rule from a recurring negative theme x product.",
        "effective_dates": "created_at <= updated_at.",
        "lifecycle": "OPEN -> IN_PROGRESS -> DONE | DISMISSED (history in action_item_event)",
        "fields": [
            f("action_item_id", "id", unique=True, rule="ACT-000001"),
            f("theme_id", "id", fk="theme.theme_id"),
            f("product_id", "id", fk="product.product_id"),
            f("priority_score", "float", unit="score", rule="DERIVED = volume x negative_share x severity_weight x (1 + shift)"),
            f("status", "enum", allowed=ACTION_STATUS, rule="= to_status of the latest action_item_event"),
            f("owner_role", "enum", allowed=["support_lead", "product_manager", "billing_ops", "logistics_ops",
                                             "marketing_ops"], rule="actor that owns the fix (by theme)"),
            f("evidence_count", "int", unit="records", rule="DERIVED = number of evidence_ids"),
            f("evidence_ids", "str", rule="'|'-separated source ids (traceability)"),
            f("created_from_rule", "str", rule="rule id + parameters that fired"),
            f("kind", "enum", allowed=["alert", "chronic"], rule="upsert key = (product_id, theme_id, kind)"),
            f("alert_id", "id", req=False, fk="alert.alert_id", rule="null for chronic items"),
            f("priority_inputs", "str", rule="JSON: volume, neg_share, severity_weight, shift"),
            f("recommendation", "str", rule="rule-based next step per theme"),
            f("created_at", "datetime"),
            f("updated_at", "datetime"),
        ],
        "relationships": [rel("theme_id", "theme", "N:1"), rel("product_id", "product", "N:1")],
    },
    "action_item_event": {
        "group": "downstream", "pk": ["event_id"], "generated": False,
        "description": "Append-only status history of action items.", "effective_dates": "event_at.",
        "lifecycle": "see action_item",
        "fields": [
            f("event_id", "id", unique=True, rule="AIE-000001"),
            f("action_item_id", "id", fk="action_item.action_item_id"),
            f("from_status", "enum", req=False, allowed=ACTION_STATUS),
            f("to_status", "enum", allowed=ACTION_STATUS),
            f("actor", "str"), f("note", "str", req=False), f("event_at", "datetime"),
        ],
        "relationships": [rel("action_item_id", "action_item", "N:1")],
    },
    "label_review_event": {
        "group": "downstream", "pk": ["event_id"], "generated": False,
        "description": "Append-only human review of eval-set labels (confirm / override).",
        "effective_dates": "event_at.", "lifecycle": None,
        "fields": [
            f("event_id", "id", unique=True, rule="LRE-000001"),
            f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
            f("old_sentiment", "enum", allowed=SENT), f("new_sentiment", "enum", allowed=SENT),
            f("old_theme_ids", "str"), f("new_theme_ids", "str"),
            f("decision", "enum", allowed=["confirmed", "overridden"]),
            f("reviewer", "str"), f("event_at", "datetime"),
        ],
        "relationships": [rel("source_id", "review / survey_response / support_message", "N:1", note="polymorphic")],
    },
    "data_exception": {
        "group": "downstream", "pk": ["exception_id"], "generated": False,
        "description": "Exception path: every failed check / detected anomaly becomes a row; nothing crashes.",
        "effective_dates": "detected_at.", "lifecycle": "OPEN -> RESOLVED | ACCEPTED",
        "fields": [
            f("exception_id", "id", unique=True, rule="EXC-000001"),
            f("table_name", "str", rule="table the offending row lives in"),
            f("record_key", "str", rule="PK of the offending row ('|'-joined if composite)"),
            f("source_type", "enum", req=False, allowed=SOURCE_TYPES, rule="feedback item the row is about (null for master data)"),
            f("source_id", "id", req=False, rule="polymorphic, as in sentiment_label"),
            f("exception_type", "str", rule="validation check name or one of the 5 issue types"),
            f("check_name", "str", rule="the check that raised it (validate/checks.py or analysis rule id)"),
            f("check_category", "enum", allowed=["validity", "integrity", "temporal", "reconciliation", "lifecycle",
                                                 "duplicate", "leakage", "privacy", "label_quality"]),
            f("disposition", "enum", allowed=["QUARANTINE", "FLAG"],
              rule="QUARANTINE = row kept in DB but excluded from analysis; FLAG = kept and shown on data-quality page"),
            f("detail", "str", rule="expected vs actual"), f("detected_by", "enum", allowed=["validation", "analysis"]),
            f("detected_at", "datetime"),
            f("resolution_status", "enum", allowed=["OPEN", "RESOLVED", "ACCEPTED"]),
        ],
        "relationships": [],
    },
    "pipeline_run": {
        "group": "downstream", "pk": ["run_id"], "generated": False,
        "description": "One execution of the analysis stages; parameters and lexicon hash make every prediction reproducible.",
        "effective_dates": "started_at <= finished_at.", "lifecycle": "SUCCEEDED | FAILED (append-only)",
        "fields": [
            f("run_id", "id", unique=True, rule="RUN-000001"),
            f("stage", "str", rule="e.g. analyze"),
            f("params", "str", rule="JSON: tau, rule settings"),
            f("lexicon_hash", "str", rule="SHA-256 (12 chars) of analyze/lexicon.py"),
            f("n_items", "int", unit="records"), f("n_auto", "int", unit="records"), f("n_review", "int", unit="records"),
            f("status", "enum", allowed=["SUCCEEDED", "FAILED"]),
            f("started_at", "datetime"), f("finished_at", "datetime"),
        ],
        "relationships": [],
    },
    "feedback_item": {
        "group": "downstream", "pk": ["source_type", "source_id"], "generated": False,
        "description": "Curated, unified feedback (reviews + survey responses + customer support messages), PII-redacted. Quarantined rows excluded.",
        "effective_dates": "event_at; week_start = Monday of the ISO week.", "lifecycle": None,
        "fields": [
            f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
            f("customer_id", "id", fk="customer.customer_id"), f("product_id", "id", fk="product.product_id"),
            f("channel_id", "id", fk="channel.channel_id"),
            f("channel_type", "enum", allowed=["survey", "review", "support"]),
            f("event_at", "datetime"), f("week_start", "date", rule="Monday of event_at's ISO week"),
            f("score_norm", "float", req=False, unit="0-1", rule="DERIVED: (rating-1)/4 or score/10; null for messages"),
            f("language", "enum", allowed=LANG, rule="declared by the source"),
            f("language_detected", "enum", allowed=LANG, rule="script + marker words"),
            f("code_mixed", "int", allowed=[0, 1], rule="1 if Latin-script Hindi/English mix"),
            f("redacted_text", "text", rule="emails, phones, known customer names replaced by [EMAIL]/[PHONE]/[NAME]"),
            f("pii_count", "int", unit="redactions"),
            f("run_id", "id", fk="pipeline_run.run_id"),
        ],
        "relationships": [rel("customer_id", "customer", "N:1"), rel("product_id", "product", "N:1"),
                          rel("channel_id", "channel", "N:1"), rel("run_id", "pipeline_run", "N:1"),
                          rel("source_id", "review / survey_response / support_message", "1:1", note="polymorphic")],
    },
    "prediction": {
        "group": "downstream", "pk": ["source_type", "source_id"], "generated": False,
        "description": "Explainable sentiment + theme prediction per feedback item, with confidence, evidence, rules and routing.",
        "effective_dates": "valid for run_id.", "lifecycle": "auto | review (human decision in label_review_event)",
        "fields": [
            f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
            f("sentiment", "enum", allowed=SENT),
            f("confidence", "float", unit="0-1", rule="rule-based certainty of the sentiment"),
            f("pos_score", "float", unit="cue weight", rule="sum of positive cue weights after negation (intensifier x1.5, litotes 0.6)"),
            f("neg_score", "float", unit="cue weight", rule="sum of negative cue weights after negation; (pos_score, neg_score) = the sentiment plane"),
            f("theme_ids", "str", req=False, rule="'|'-separated, most specific theme; null = unclassified"),
            f("evidence", "str", req=False, rule="'|'-separated matched cues, e.g. +recommend|-never arrives"),
            f("rules_fired", "str", rule="'|'-separated rule ids, e.g. LEX|NEGATION|CONTRAST"),
            f("route", "enum", allowed=["auto", "review"], rule="review if confidence < tau or a risk rule fired"),
            f("route_reason", "str", req=False),
            f("run_id", "id", fk="pipeline_run.run_id"),
        ],
        "relationships": [rel("run_id", "pipeline_run", "N:1"),
                          rel("source_id", "feedback_item", "1:1", note="same (source_type, source_id)")],
    },
    "weekly_cell": {
        "group": "downstream", "pk": ["cell_id"], "generated": False,
        "description": "Aggregate cube: product x theme x channel_type x ISO week. Members listed in cell_member (lineage).",
        "effective_dates": "week_start (Monday).", "lifecycle": None,
        "fields": [
            f("cell_id", "id", unique=True, rule="CELL-<week_start>-<product_id>-<theme_id>-<channel_type>"),
            f("week_start", "date"), f("product_id", "id", fk="product.product_id"),
            f("theme_id", "id", fk="theme.theme_id"),
            f("channel_type", "enum", allowed=["survey", "review", "support"]),
            f("n_items", "int", unit="records", rule="DERIVED = members in cell_member"),
            f("n_negative", "int", unit="records", rule="DERIVED: predicted negative"),
            f("neg_share", "float", unit="0-1", rule="DERIVED = n_negative / n_items"),
            f("mean_score", "float", req=False, unit="0-1", rule="DERIVED mean score_norm (null for support)"),
            f("run_id", "id", fk="pipeline_run.run_id"),
        ],
        "relationships": [rel("product_id", "product", "N:1"), rel("theme_id", "theme", "N:1"),
                          rel("run_id", "pipeline_run", "N:1")],
    },
    "cell_member": {
        "group": "downstream", "pk": ["cell_id", "source_type", "source_id"], "generated": False,
        "description": "Lineage bridge: which feedback items make up each weekly cell (cell N:M feedback item).",
        "effective_dates": "-", "lifecycle": None,
        "fields": [f("cell_id", "id", fk="weekly_cell.cell_id"), f("source_type", "enum", allowed=SOURCE_TYPES),
                   f("source_id", "id")],
        "relationships": [rel("cell_id", "weekly_cell", "N:1"),
                          rel("source_id", "feedback_item", "N:1", note="polymorphic via source_type")],
    },
    "alert": {
        "group": "downstream", "pk": ["alert_id"], "generated": False,
        "description": "Detected sentiment shift for a product x theme: rolling 7-day window vs 28-day baseline, evaluated daily.",
        "effective_dates": "start_date (first firing day) <= peak_date <= end_date.",
        "lifecycle": "ACTIVE -> ENDED (DERIVED: ENDED if no firing in the last 3 days of data)",
        "fields": [
            f("alert_id", "id", unique=True, rule="ALR-000001, ordered by start_date"),
            f("product_id", "id", fk="product.product_id"), f("theme_id", "id", fk="theme.theme_id"),
            f("direction", "enum", allowed=["worsen", "improve"]),
            f("kind", "enum", allowed=["worsen", "improve", "recovery"],
              rule="recovery = improve on a key whose worsen alert ended within 28 days"),
            f("start_date", "date", rule="first firing day of the run"),
            f("detected_date", "date", rule="confirmation day (3rd firing day) - used for time-to-detect"),
            f("peak_date", "date"), f("end_date", "date"),
            f("status", "enum", allowed=["ACTIVE", "ENDED"]),
            f("magnitude", "float", unit="M", rule="M = -log10(p) at peak; worsen: exact Poisson tail, improve: normal tail; M >= 5 <=> p <= 1e-5"),
            f("peak_z", "float", unit="z", rule="worsen: (obs-lam)/sqrt(lam) at peak (gate: exact Poisson p<=1e-5); improve: share drop / se"),
            f("baseline_share", "float", unit="0-1"), f("window_share", "float", unit="0-1"),
            f("shift", "float", unit="share points", rule="window_share - baseline_share at peak"),
            f("window_items", "int", unit="records"),
            f("lead_channel", "enum", req=False, allowed=["support", "review", "survey"],
              rule="channel whose own series fired first"),
            f("first_support_date", "date", req=False), f("first_review_date", "date", req=False),
            f("first_survey_date", "date", req=False),
            f("evidence_count", "int", unit="records", rule="DERIVED = rows in alert_evidence"),
            f("run_id", "id", fk="pipeline_run.run_id"),
        ],
        "relationships": [rel("product_id", "product", "N:1"), rel("theme_id", "theme", "N:1"),
                          rel("run_id", "pipeline_run", "N:1")],
    },
    "alert_evidence": {
        "group": "downstream", "pk": ["alert_id", "source_type", "source_id"], "generated": False,
        "description": "Lineage: the feedback items behind an alert (trigger window and peak window).",
        "effective_dates": "-", "lifecycle": None,
        "fields": [f("alert_id", "id", fk="alert.alert_id"), f("source_type", "enum", allowed=SOURCE_TYPES),
                   f("source_id", "id"), f("role", "enum", allowed=["trigger", "peak"])],
        "relationships": [rel("alert_id", "alert", "N:1"),
                          rel("source_id", "feedback_item", "N:1", note="polymorphic via source_type")],
    },
    "eval_review_sample": {
        "group": "downstream", "pk": ["source_type", "source_id"], "generated": False,
        "description": "Blind human-review sample of the eval split (stratified by gold sentiment, built by evaluate/). "
                       "Holds NO label, so reviewers and the API never see the gold answer.",
        "effective_dates": "-", "lifecycle": "pending -> reviewed (via label_review_event)",
        "fields": [f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
                   f("sample_rank", "int", unique=True, rule="review order 1..n (shuffled)")],
        "relationships": [rel("source_id", "feedback_item", "1:1", note="polymorphic via source_type")],
    },
    # ------------------------------------------------------------------ ground truth (evaluation only)
    "gt_labels": {
        "group": "ground_truth", "pk": ["source_type", "source_id"], "generated": True, "file": "labels.csv",
        "description": "Gold labels for EVERY labelled feedback item, decided by the template that produced the text.",
        "effective_dates": "-", "lifecycle": None,
        "fields": [
            f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
            f("sentiment", "enum", allowed=SENT),
            f("theme_ids", "str", rule="'|'-separated THEME ids, most specific theme"),
            f("style", "enum", allowed=STYLES), f("language", "enum", allowed=LANG),
            f("template_id", "str", rule="frame id, e.g. EN-SARCASTIC-NEG-02 / TE-MIX-01"),
            f("incident_id", "id", req=False, rule="incident that caused this item"),
            f("incident_phase", "enum", req=False, allowed=["pre", "post"]),
            f("product_id", "id"), f("split", "enum", allowed=["train", "eval"], rule="eval stratified by sentiment"),
        ],
        "relationships": [],
    },
    "gt_incidents": {
        "group": "ground_truth", "pk": ["incident_id"], "generated": True, "file": "incidents.csv",
        "description": "Hidden incidents that cause sentiment shifts, with explicit per-channel lag (support 0, review +3, survey +7 days).",
        "effective_dates": "onset_date..end_date; <channel>_signal_start = onset + lag.", "lifecycle": None,
        "fields": [
            f("incident_id", "id"), f("name", "str"), f("description", "str"), f("product_id", "id"),
            f("direction", "enum", allowed=["worsen", "improve"]), f("theme_id", "id"),
            f("onset_date", "date"), f("end_date", "date"),
            f("lag_support_days", "int", unit="days"), f("support_signal_start", "date"),
            f("lag_review_days", "int", unit="days"), f("review_signal_start", "date"),
            f("lag_survey_days", "int", unit="days"), f("survey_signal_start", "date"),
            f("volume_boost", "float", unit="x extra weight"), f("override_prob", "float", unit="probability"),
            f("pre_onset_prob", "float", unit="probability"),
            f("n_support_items", "int", unit="records", rule="DERIVED count of caused items"),
            f("n_review_items", "int", unit="records"), f("n_survey_items", "int", unit="records"),
        ],
        "relationships": [],
    },
    "gt_anomalies": {
        "group": "ground_truth", "pk": ["anomaly_id"], "generated": True, "file": "anomalies.csv",
        "description": "The 5 planted edge-case types with the decision the pipeline is expected to take.",
        "effective_dates": "-", "lifecycle": None,
        "fields": [
            f("anomaly_id", "id", unique=True, rule="ANOM-0001"),
            f("issue_type", "enum", allowed=ISSUE_TYPES),
            f("source_type", "enum", allowed=SOURCE_TYPES), f("source_id", "id"),
            f("detail", "str"), f("expected_decision", "str"),
        ],
        "relationships": [],
    },
}

INPUT_TABLES = [k for k, e in ENTITIES.items() if e["generated"] and e["group"] != "ground_truth"]
SQL_TYPES = {"id": "TEXT", "str": "TEXT", "text": "TEXT", "enum": "TEXT", "int": "INTEGER", "float": "NUMERIC",
             "date": "DATE", "datetime": "TIMESTAMP"}
GROUP_TITLES = {"master": "Master data", "feedback": "Feedback (children)", "events": "Event history (append-only)",
                "labels": "Labels and bridge tables (input)", "downstream": "Created later by analysis / validation",
                "ground_truth": "Ground truth - evaluation only (data/output/ground_truth/)"}


def columns(table: str) -> list[str]:
    return [x["name"] for x in ENTITIES[table]["fields"]]


def render_markdown() -> str:
    out = ["# VoiceLens data dictionary", "",
           "> Generated from `backend/voicelens/generate/contract.py` (single source of truth; the validator uses the same contract).",
           "> Regenerate: `python -m voicelens.generate.contract` (from `backend/`).", "",
           "Conventions: IDs are zero-padded and immutable and identical across files. Dates are ISO `YYYY-MM-DD`, "
           "datetimes are `YYYY-MM-DD HH:MM:SS` (synthetic local time). Reference date (\"today\") = 2026-10-01. "
           "Feedback window = 2026-04-06 .. 2026-09-27 (25 ISO weeks). All text is synthetic.", "",
           "## Relationships and cardinality", "",
           "| Child.field | Parent | Cardinality | Optional | Note |", "|---|---|---|---|---|"]
    for name, e in ENTITIES.items():
        for r in e["relationships"]:
            out.append(f"| {name}.{r['field']} | {r['parent']} | {r['cardinality']} | "
                       f"{'yes' if r['optional'] else 'no'} | {r['note']} |")
    out += ["", "Derived N:M: feedback N:M theme via `feedback_theme`. 1:N summary: customer 1:N reviews/responses/"
            "tickets; survey 1:N responses; ticket 1:N messages and 1:N status events; theme 1:N action items; "
            "action item 1:N events.", ""]
    group = None
    for name, e in ENTITIES.items():
        if e["group"] != group:
            group = e["group"]
            out += [f"## {GROUP_TITLES[group]}", ""]
        title = f"`{name}`" + (f" -> `{e['file']}`" if e.get("file") else "")
        out += [f"### {title}", "", e["description"], "",
                f"- **Primary key:** {', '.join(e['pk'])}",
                f"- **Effective dates:** {e['effective_dates']}",
                f"- **Lifecycle:** {e['lifecycle'] or 'none (immutable record)'}",
                f"- **Produced by:** {'generator' if e['generated'] else 'analysis / validation pipeline'}", "",
                "| Field | Type | Required | Allowed values | Unit | Unique | FK | Validation rule |",
                "|---|---|---|---|---|---|---|---|"]
        for x in e["fields"]:
            allowed = ", ".join(map(str, x["allowed"])) if x["allowed"] else ""
            if x["allowed"] and len(x["allowed"]) == 11:
                allowed = "0..10"
            out.append(f"| {x['name']} | {x['type']} | {'yes' if x['required'] else 'no'} | {allowed} | {x['unit']} | "
                       f"{'yes' if x['unique'] else ''} | {x['fk'] or ''} | {x['rule']} |")
        out.append("")
    out += ["## ID formats", "", "| Field | Pattern |", "|---|---|"]
    out += [f"| {k} | `{v}` |" for k, v in ID_PATTERNS.items()]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "docs" / "DATA_DICTIONARY.md"
    target.write_text(render_markdown(), encoding="utf-8", newline="\n")
    print(f"wrote {target}")
