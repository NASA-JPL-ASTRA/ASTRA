"""
ASTRA Backend - Main Application
NASA JPL Testbed Recording and Analysis System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import sessions, notes, telemetry, websocket, stt   # added stt

app = FastAPI(
    title="ASTRA Backend",
    description="Advanced System for Testbed Recording and Analysis - NASA JPL Capstone Project",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router,  prefix="/api/sessions", tags=["Sessions"])
app.include_router(notes.router,     prefix="/api/sessions", tags=["Notes"])
app.include_router(telemetry.router, prefix="/api/sessions", tags=["Telemetry"])
app.include_router(stt.router,       prefix="/api/sessions", tags=["STT"])        # added
app.include_router(websocket.router, prefix="/ws/sessions",  tags=["WebSocket"])


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "ASTRA Backend",
        "version": "0.2.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
