# VoiceLens evaluation

Run `RUN-000001` · rules `f38106526d6c` · evaluated 2026-11-15 16:38:25. Rules were tuned on TRAIN only; EVAL is the honest number.

## Sentiment

| Split | Items | Accuracy | Macro-F1 | Coverage (auto) | Auto accuracy | Theme exact | Theme micro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eval | 1,960 | 94.1% | 0.941 | 83.8% | 98.8% | 94.1% | 0.958 |
| train (tuned on) | 58,952 | 94.6% | 0.946 | 84.1% | 98.8% | 93.8% | 0.955 |

Eval items excluded by the ingest gate (quarantined): 40.

Confusion matrix (eval, rows = gold, columns = predicted):

| gold \ pred | positive | negative | neutral | mixed |
|---|---:|---:|---:|---:|
| positive | 491 | 0 | 0 | 0 |
| negative | 0 | 453 | 0 | 35 |
| neutral | 0 | 25 | 466 | 0 |
| mixed | 19 | 27 | 10 | 434 |

## By style (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| ambiguous | 99 | 74.8% | 41.4% | 56.1% | 91.9% |
| mixed | 406 | 87.9% | 88.2% | 99.7% | 98.5% |
| multilingual | 409 | 98.3% | 92.9% | 100.0% | 89.5% |
| negation | 127 | 72.4% | 72.4% | 100.0% | 89.8% |
| plain | 849 | 100.0% | 88.7% | 100.0% | 94.7% |
| sarcastic | 70 | 100.0% | 27.1% | 100.0% | 100.0% |

## By language (eval)

| Slice | n | Accuracy | Coverage | Auto accuracy | Theme exact |
|---|---:|---:|---:|---:|---:|
| en | 1551 | 93.0% | 81.4% | 98.5% | 95.4% |
| es | 108 | 100.0% | 100.0% | 100.0% | 91.7% |
| hi | 84 | 100.0% | 83.3% | 100.0% | 83.3% |
| hi-Latn | 95 | 92.6% | 84.2% | 100.0% | 89.5% |
| te | 122 | 100.0% | 100.0% | 100.0% | 91.8% |

## Accuracy vs coverage (abstention threshold tau)

Rule: max train coverage with auto accuracy >= 0.95. Current tau 0.6 -> recommended **0.45** (train: coverage 95.3%, auto accuracy 95.2%; eval: coverage 95.4%, auto accuracy 94.9%).

| tau | Eval coverage | Eval auto accuracy |
|---:|---:|---:|
| 0.3 | 96.1% | 94.6% |
| 0.35 | 96.1% | 94.6% |
| 0.4 | 96.1% | 94.6% |
| 0.45 | 95.4% | 94.9% |
| 0.5 | 94.1% | 94.8% |
| 0.55 | 87.9% | 94.7% |
| 0.6 | 83.8% | 98.8% |
| 0.65 | 80.8% | 98.9% |
| 0.7 | 80.0% | 98.9% |
| 0.75 | 72.0% | 100.0% |
| 0.8 | 67.5% | 100.0% |
| 0.85 | 16.1% | 100.0% |
| 0.9 | 7.5% | 100.0% |
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
| INC-01 | worsen | 2026-07-20 | ALR-000006 | 2026-07-25 | 5 | support | 1 vs 0 / 3 vs 3 / 7 vs 7 | 93.9% |
| INC-02 | worsen | 2026-06-22 | ALR-000003 | 2026-06-27 | 5 | support | 0 vs 0 / 3 vs 3 / 7 vs 7 | 91.2% |
| INC-03 | worsen | 2026-05-11 | ALR-000001 | 2026-05-14 | 3 | support | 0 vs 0 / 1 vs 3 / 11 vs 7 | 92.5% |
| INC-04 | improve | 2026-08-24 | ALR-000009 | 2026-09-01 | 8 | support | -1 vs 0 / 6 vs 3 / 9 vs 7 | 83.6% |

## Human-reviewed evaluation set

Blind sample of 100 eval items (stratified by gold sentiment, label hidden from reviewers). Reviewed so far: **0** (0 review events in total).
Open the Review queue -> 'Evaluation set' tab to label them; rerun evaluation to fill this section.
