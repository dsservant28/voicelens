"""Theme classification: cue terms = raw.theme.keywords (the business taxonomy in the DB) + analyze/lexicon.THEMES
(multilingual). Product names are masked first (they are master data, not opinions). The text is split into
contrast clauses; each clause contributes its first theme (a child theme beats its parent), at most MAX_THEMES."""
from __future__ import annotations

import re

import pandas as pd

from . import lexicon as L
from .matcher import Matcher

MAX_THEMES = 2


class ThemeClassifier:
    def __init__(self, theme: pd.DataFrame, product_names: list[str]):
        self.id_of = dict(zip(theme["code"], theme["theme_id"]))
        code_of_id = dict(zip(theme["theme_id"], theme["code"]))
        self.parent = {c: code_of_id.get(p) for c, p in zip(theme["code"], theme["parent_theme_id"]) if p}
        groups: dict[str, list[str]] = {}
        for code in sorted(theme["code"], key=lambda c: c not in self.parent):      # children first on ties
            kw = theme.loc[theme["code"] == code, "keywords"].iloc[0] or ""
            groups[code] = L.terms(kw + "|" + L.THEMES.get(code, ""))
        self.matcher = Matcher(groups)
        self.splitter = Matcher({"c": L.terms(L.CLAUSE_SPLIT)})
        self.products = re.compile("|".join(re.escape(n.lower()) for n in sorted(product_names, key=len, reverse=True)))

    def classify(self, text: str) -> tuple[list[str], list[str]]:
        """-> (theme_ids, evidence like '#late_delivery:delayed')."""
        low = self.products.sub(" [product] ", text.lower())
        bounds = [m.start for m in self.splitter.find(low)]
        hits = self.matcher.find(low)
        codes, evidence = [], []
        for clause in sorted({sum(b < h.start for b in bounds) for h in hits}):
            ch = [h for h in hits if sum(b < h.start for b in bounds) == clause]
            kinds = list(dict.fromkeys(h.kind for h in ch))
            kinds = [k for k in kinds if k not in {self.parent.get(x) for x in kinds}]   # most specific wins
            if kinds and kinds[0] not in codes:
                codes.append(kinds[0])
                evidence += [f"#{h.kind}:{h.term}" for h in ch if h.kind == kinds[0]]
        codes = codes[:MAX_THEMES]
        return [self.id_of[c] for c in codes], list(dict.fromkeys(e for e in evidence if e.split(":")[0][1:] in codes))
