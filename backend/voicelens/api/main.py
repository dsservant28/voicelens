"""VoiceLens API.  Run from backend/:  uvicorn voicelens.api.main:app --reload   ->  http://localhost:8000/docs"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import actions, alerts, feedback, overview, quality, themes

app = FastAPI(title="VoiceLens API", version="1.0",
              description="Customer feedback intelligence: early-warning alerts, explainable predictions, "
                          "human review and action items - every number traceable to source records.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (overview, themes, alerts, feedback, actions, quality):
    app.include_router(r.router)
