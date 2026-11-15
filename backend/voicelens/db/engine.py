"""Engine from DATABASE_URL in the repo-root .env (git-ignored). No credentials in code."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def database_url() -> str:
    load_dotenv(ENV_FILE)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit(f"DATABASE_URL is not set (expected in {ENV_FILE}; see .env.example)")
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    return url


def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)
