"""Stage 4 - abstain: decide auto vs human review, with every reason recorded. Never guess silently."""
from __future__ import annotations

TAU = 0.6                      # default; chosen from the accuracy-vs-coverage curve in evaluation
RATING_LOW, RATING_HIGH = 0.35, 0.75
LABEL_CONFLICT_MIN_CONF = 0.7


def route(pred: dict, n_themes: int, score_norm: float | None, label_conflict: bool, tau: float = TAU) -> tuple[str, str]:
    reasons = []
    if pred["confidence"] < tau:
        reasons.append("LOW_CONFIDENCE")
    if "SARCASM" in pred["rules"]:
        reasons.append("SARCASM")
    if n_themes == 0:
        reasons.append("NO_THEME")
    if score_norm is not None and score_norm == score_norm:          # not NaN
        if (pred["sentiment"] == "positive" and score_norm < RATING_LOW) or \
                (pred["sentiment"] == "negative" and score_norm > RATING_HIGH):
            reasons.append("RATING_CONFLICT")
    if label_conflict:
        reasons.append("LABEL_CONFLICT")
    return ("review" if reasons else "auto"), "|".join(reasons)
