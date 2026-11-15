# VoiceLens evaluation

Run `RUN-000001` · rules `6efd32b35cd8` · evaluated 2026-11-15 18:24:22. Rules were tuned on TRAIN only; EVAL is the honest number.

## Sentiment

| Split | Items | Accuracy | Macro-F1 | Coverage (auto) | Auto accuracy | Theme exact | Theme micro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eval | 1,960 | 94.2% | 0.942 | 83.5% | 98.5% | 93.1% | 0.951 |
| train (tuned on) | 59,243 | 94.6% | 0.946 | 84.1% | 98.9% | 93.9% | 0.955 |

Eval items excluded by the ingest gate (quarantined): 40.

Confusion matrix (eval, rows = gold, columns = predicted):

| gold \ pred | positive | negative | neutral | mixed |
|---|---:|---:|---:|---:|
| positive | 491 | 0 | 0 | 0 |
| negative | 0 | 453 | 3 | 32 |
| neutral | 0 | 28 | 464 | 0 |
| mixed | 18 | 22 | 10 | 439 |

## By style (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| ambiguous | 99 | 71.7% | 50.5% | 50.0% | 98.0% |
| mixed | 388 | 88.9% | 88.9% | 100.0% | 97.7% |
| multilingual | 385 | 98.2% | 91.7% | 100.0% | 86.5% |
| negation | 153 | 79.1% | 79.1% | 100.0% | 94.8% |
| plain | 868 | 100.0% | 87.2% | 100.0% | 92.5% |
| sarcastic | 67 | 95.5% | 16.4% | 100.0% | 100.0% |

## By language (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| en | 1575 | 93.3% | 81.5% | 98.0% | 94.7% |
| es | 99 | 100.0% | 100.0% | 100.0% | 90.9% |
| hi | 82 | 100.0% | 85.4% | 100.0% | 74.4% |
| hi-Latn | 89 | 92.1% | 77.5% | 100.0% | 85.4% |
| te | 115 | 100.0% | 100.0% | 100.0% | 92.2% |

## Accuracy vs coverage (abstention threshold tau)

Rule: max train coverage with auto accuracy >= 0.95. Current tau 0.6 -> recommended **0.45** (train: coverage 95.2%, auto accuracy 95.2%; eval: coverage 95.2%, auto accuracy 94.8%).

| tau | Eval coverage | Eval auto accuracy |
|---:|---:|---:|
| 0.3 | 96.2% | 94.5% |
| 0.35 | 96.2% | 94.5% |
| 0.4 | 96.2% | 94.5% |
| 0.45 | 95.2% | 94.8% |
| 0.5 | 94.2% | 94.8% |
| 0.55 | 87.2% | 94.7% |
| 0.6 | 83.5% | 98.5% |
| 0.65 | 80.7% | 98.4% |
| 0.7 | 79.7% | 98.4% |
| 0.75 | 71.5% | 100.0% |
| 0.8 | 67.4% | 100.0% |
| 0.85 | 17.3% | 100.0% |
| 0.9 | 8.1% | 100.0% |
| 0.95 | 0.0% | - |

## Edge cases (planted vs detected)

| Issue type | Planted | Detected | Recall | Precision | Expected decision | Decision correct |
|---|---:|---:|---:|---:|---|---:|
| DUPLICATE_RESPONSE | 40 | 40 | 100.0% | 100.0% | drop_duplicate_keep_first | 40/40 |
| LABEL_CONTRADICTS_TEXT | 40 | 40 | 100.0% | 100.0% | flag_for_human_review | 40/40 |
| PII_LEAK | 40 | 40 | 100.0% | 100.0% | redact_before_analysis | 40/40 |
| TEST_LABEL_IN_MODEL_INPUT | 40 | 40 | 100.0% | 100.0% | strip_tag_and_exclude_from_eval | 40/40 |
| THEME_OUTSIDE_TAXONOMY | 40 | 40 | 100.0% | 100.0% | reject_link_and_log_exception | 40/40 |

## Incident detection (early warning)

Detected **4/4**, false alarms **0**, recoveries 4, mean time-to-detect **5.25 days**, lead channel correct 4/4.

| Incident | Direction | Onset | Alert | Detected | Days | Lead | Lag support/review/survey (measured vs designed) | Evidence precision |
|---|---|---|---|---|---:|---|---|---:|
| INC-01 | worsen | 2026-07-20 | ALR-000006 | 2026-07-25 | 5 | support | 0 vs 0 / 3 vs 3 / 7 vs 7 | 94.0% |
| INC-02 | worsen | 2026-06-22 | ALR-000003 | 2026-06-27 | 5 | support | 0 vs 0 / 3 vs 3 / 7 vs 7 | 91.7% |
| INC-03 | worsen | 2026-05-11 | ALR-000001 | 2026-05-14 | 3 | support | 0 vs 0 / 1 vs 3 / 11 vs 7 | 92.4% |
| INC-04 | improve | 2026-08-24 | ALR-000010 | 2026-09-01 | 8 | support | 3 vs 0 / 6 vs 3 / 9 vs 7 | 85.3% |

## Human-reviewed evaluation set

Blind sample of 100 eval items (stratified by gold sentiment, label hidden from reviewers). Reviewed so far: **0** (0 review events in total).
Open the Review queue -> 'Evaluation set' tab to label them; rerun evaluation to fill this section.
