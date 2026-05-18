"""
ASTRA Backend - Main Application
NASA JPL Testbed Recording and Analysis System
"""

# Load environment variables from backend/.env BEFORE importing any module
# that reads them at import time (e.g. app.services.openai_stt).
import logging
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_ROOT / ".env")

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sessions, notes, telemetry, websocket, stt, structure_notes

logger = logging.getLogger(__name__)


def get_cors_origins() -> list[str]:
    default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://astra-git-main-volcano-mites-projects.vercel.app",
        "https://astra-qtlz6uxdg-volcano-mites-projects.vercel.app",
    ]
    extra_origins = [
        origin.strip()
        for origin in os.getenv("BACKEND_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys(default_origins + extra_origins))


try:
    from app.routes import telemetry_query
except ImportError as e:
    telemetry_query = None
    logger.warning(
        "Telemetry query routes disabled (import error): %s. "
        "Install backend deps: pip install -r requirements.txt",
        e,
    )


app = FastAPI(
    title="ASTRA Backend",
    description="Advanced System for Testbed Recording and Analysis - NASA JPL Capstone Project",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router,  prefix="/api/sessions", tags=["Sessions"])
app.include_router(structure_notes.router, prefix="/api/sessions", tags=["Structure Notes"])
app.include_router(notes.router,     prefix="/api/sessions", tags=["Notes"])
app.include_router(telemetry.router, prefix="/api/sessions", tags=["Telemetry"])
app.include_router(stt.router,       prefix="/api/sessions", tags=["STT"])
app.include_router(websocket.router, prefix="/ws/sessions",  tags=["WebSocket"])
if telemetry_query is not None:
    app.include_router(telemetry_query.router, prefix="/api", tags=["Telemetry Query"])


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "ASTRA Backend",
        "version": "0.3.0",
        "docs": "/docs",
        "telemetry_query_api": telemetry_query is not None,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
