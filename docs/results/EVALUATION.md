# VoiceLens evaluation

Run `RUN-000001` · rules `6f28b647f931` · evaluated 2026-11-15 16:23:14. Rules were tuned on TRAIN only; EVAL is the honest number.

## Sentiment

| Split | Items | Accuracy | Macro-F1 | Coverage (auto) | Auto accuracy | Theme exact | Theme micro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eval | 490 | 94.9% | 0.949 | 82.7% | 98.8% | 93.1% | 0.949 |
| train (tuned on) | 14,754 | 95.0% | 0.950 | 84.4% | 98.7% | 94.4% | 0.958 |

Eval items excluded by the ingest gate (quarantined): 10.

Confusion matrix (eval, rows = gold, columns = predicted):

| gold \ pred | positive | negative | neutral | mixed |
|---|---:|---:|---:|---:|
| positive | 122 | 0 | 0 | 0 |
| negative | 0 | 116 | 0 | 6 |
| neutral | 0 | 8 | 115 | 0 |
| mixed | 6 | 3 | 2 | 112 |

## By style (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| ambiguous | 24 | 66.7% | 37.5% | 44.4% | 91.7% |
| mixed | 100 | 89.0% | 89.0% | 100.0% | 99.0% |
| multilingual | 102 | 100.0% | 94.1% | 100.0% | 80.4% |
| negation | 38 | 84.2% | 84.2% | 100.0% | 92.1% |
| plain | 204 | 100.0% | 85.8% | 100.0% | 96.1% |
| sarcastic | 22 | 100.0% | 18.2% | 100.0% | 100.0% |

## By language (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| en | 388 | 93.6% | 79.6% | 98.4% | 96.4% |
| es | 30 | 100.0% | 100.0% | 100.0% | 90.0% |
| hi | 18 | 100.0% | 77.8% | 100.0% | 55.6% |
| hi-Latn | 23 | 100.0% | 91.3% | 100.0% | 78.3% |
| te | 31 | 100.0% | 100.0% | 100.0% | 87.1% |

## Accuracy vs coverage (abstention threshold tau)

Rule: max train coverage with auto accuracy >= 0.95. Current tau 0.6 -> recommended **0.3** (train: coverage 95.9%, auto accuracy 95.2%; eval: coverage 95.1%, auto accuracy 95.7%).

| tau | Eval coverage | Eval auto accuracy |
|---:|---:|---:|
| 0.3 | 95.1% | 95.7% |
| 0.35 | 95.1% | 95.7% |
| 0.4 | 95.1% | 95.7% |
| 0.45 | 94.7% | 95.7% |
| 0.5 | 93.1% | 95.6% |
| 0.55 | 86.1% | 95.7% |
| 0.6 | 82.7% | 98.8% |
| 0.65 | 79.4% | 98.7% |
| 0.7 | 79.0% | 98.7% |
| 0.75 | 70.0% | 100.0% |
| 0.8 | 64.7% | 100.0% |
| 0.85 | 14.9% | 100.0% |
| 0.9 | 5.7% | 100.0% |
| 0.95 | 0.0% | - |

## Edge cases (planted vs detected)

| Issue type | Planted | Detected | Recall | Precision | Expected decision | Decision correct |
|---|---:|---:|---:|---:|---|---:|
| DUPLICATE_RESPONSE | 10 | 10 | 100.0% | 100.0% | drop_duplicate_keep_first | 10/10 |
| LABEL_CONTRADICTS_TEXT | 10 | 10 | 100.0% | 100.0% | flag_for_human_review | 10/10 |
| PII_LEAK | 10 | 10 | 100.0% | 100.0% | redact_before_analysis | 10/10 |
| TEST_LABEL_IN_MODEL_INPUT | 10 | 10 | 100.0% | 100.0% | strip_tag_and_exclude_from_eval | 10/10 |
| THEME_OUTSIDE_TAXONOMY | 10 | 10 | 100.0% | 100.0% | reject_link_and_log_exception | 10/10 |

## Incident detection (early warning)

Detected **4/4**, false alarms **0**, recoveries 1, mean time-to-detect **7.0 days**, lead channel correct 3/4.

| Incident | Direction | Onset | Alert | Detected | Days | Lead | Lag support/review/survey (measured vs designed) | Evidence precision |
|---|---|---|---|---|---:|---|---|---:|
| INC-01 | worsen | 2026-07-20 | ALR-000004 | 2026-07-26 | 6 | support | 1 vs 0 / 3 vs 3 / 10 vs 7 | 94.0% |
| INC-02 | worsen | 2026-06-22 | ALR-000003 | 2026-06-30 | 8 | support | 3 vs 0 / 5 vs 3 / 12 vs 7 | 97.6% |
| INC-03 | worsen | 2026-05-11 | ALR-000001 | 2026-05-16 | 5 | support | 2 vs 0 / 3 vs 3 / - vs 7 | 89.7% |
| INC-04 | improve | 2026-08-24 | ALR-000005 | 2026-09-02 | 9 | review | 7 vs 0 / 3 vs 3 / 10 vs 7 | 81.0% |

## Human review

0 review events. None yet - the review queue screen fills this section.
