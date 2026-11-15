"""Longest-first phrase matcher. Latin scripts use word boundaries; Devanagari/Telugu use substring matching
(Python's \\b breaks inside Indic words because vowel signs are not 'word' characters)."""
from __future__ import annotations

import re
from dataclasses import dataclass

LATIN_TOKEN = re.compile(r"[\w'’-]+")
INDIC = re.compile(r"[ऀ-ॿఀ-౿]")


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    term: str
    kind: str


class Matcher:
    def __init__(self, groups: dict[str, list[str]]):
        """groups: kind -> terms. Earlier kinds win ties; longer terms always win."""
        self.kind_of: dict[str, str] = {}
        for kind, ts in groups.items():
            for t in ts:
                self.kind_of.setdefault(t, kind)
        allt = sorted(self.kind_of, key=lambda t: (-len(t), t))
        latin = [re.escape(t) for t in allt if not INDIC.search(t)]
        indic = [re.escape(t) for t in allt if INDIC.search(t)]
        parts = []
        if latin:
            parts.append(r"(?<![\w'])(?:" + "|".join(latin) + r")(?![\w'])")
        if indic:
            parts.append("(?:" + "|".join(indic) + ")")
        self.rx = re.compile("|".join(parts)) if parts else None

    def find(self, text: str) -> list[Match]:
        if not self.rx:
            return []
        return [Match(m.start(), m.end(), m.group(0), self.kind_of[m.group(0)]) for m in self.rx.finditer(text)]


def tokens_before(text: str, pos: int, n: int) -> list[str]:
    return [t.lower() for t in LATIN_TOKEN.findall(text[:pos])[-n:]] if not INDIC.search(text) else text[:pos].split()[-n:]


def tokens_after(text: str, pos: int, n: int) -> list[str]:
    return [t.strip(".,!?।") for t in text[pos:].split()[:n]]
