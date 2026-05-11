"""
AiSTRA Backend - Main Application
AI System for Testbed Recording and Analysis — NASA JPL Capstone Project
"""

# Load .env BEFORE importing modules that read env vars at import time
# (e.g. app.services.openai_stt reads OPENAI_API_KEY)
import logging
from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sessions, notes, telemetry, websocket, stt

logger = logging.getLogger(__name__)


def get_cors_origins() -> list[str]:
    """Build CORS allow-list: defaults + any extra from BACKEND_CORS_ORIGINS env."""
    default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Ryan's Vercel deployment
        "https://astra-git-main-volcano-mites-projects.vercel.app",
        "https://astra-qtlz6uxdg-volcano-mites-projects.vercel.app",
    ]
    extra_origins = [
        origin.strip()
        for origin in os.getenv("BACKEND_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    return list(dict.fromkeys(default_origins + extra_origins))


# Optional: Yuyang's telemetry query routes (requires influxdb-client, scikit-learn)
try:
    from app.routes import telemetry_query
except (ImportError, ModuleNotFoundError) as e:
    telemetry_query = None
    logger.warning("Telemetry query routes disabled: %s", e)


app = FastAPI(
    title="AiSTRA Backend",
    description="AI System for Testbed Recording and Analysis - NASA JPL Capstone Project",
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
        "service": "AiSTRA Backend",
        "version": "0.3.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
