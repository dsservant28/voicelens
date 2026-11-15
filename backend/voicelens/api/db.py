"""Thin query helpers over the shared engine (plain SQL, parameterised)."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, text

from ..db.engine import get_engine


@lru_cache(maxsize=1)
def engine() -> Engine:
    return get_engine()


def rows(sql: str, **params) -> list[dict]:
    with engine().connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), params)]


def one(sql: str, **params) -> dict | None:
    r = rows(sql, **params)
    return r[0] if r else None


def scalar(sql: str, **params):
    with engine().connect() as c:
        return c.execute(text(sql), params).scalar()


def execute(statements: list[tuple[str, dict]]) -> None:
    """Run several writes in one transaction."""
    with engine().begin() as c:
        for sql, params in statements:
            c.execute(text(sql), params)


ITEM_SQL = """
SELECT f.source_type, f.source_id, f.product_id, pr.name AS product_name, f.channel_type, f.event_at, f.language,
       f.redacted_text, p.sentiment, p.confidence, p.theme_ids, p.route, p.route_reason, p.rules_fired, p.evidence
FROM app.feedback_item f JOIN app.prediction p USING (source_type, source_id)
JOIN raw.product pr ON pr.product_id = f.product_id
"""
