"""
Log-file voice telemetry API (event.log / channel.log on disk).

Endpoints:
- GET  /api/telemetry/log-scenarios
- GET  /api/sessions/{sid}/telemetry/voice-queries
- POST /api/sessions/{sid}/telemetry/voice-query
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    add_voice_telemetry_query,
    get_session,
    get_voice_telemetry_queries,
)
from app.services import log_telemetry
from app.ws_manager import (
    EVENT_TELEMETRY_QUERY_DONE,
    EVENT_TELEMETRY_QUERY_STARTED,
    broadcast,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class VoiceTelemetryQueryRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    scenario: str | None = None


class VoiceTelemetryQueryResponse(BaseModel):
    id: str
    session_id: str
    transcript: str
    action: str
    scenario: str
    intent: dict[str, Any]
    answer: str
    is_telemetry_query: bool
    created_at: datetime


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/telemetry/log-scenarios")
def list_log_scenarios() -> dict[str, Any]:
    root = log_telemetry.get_telemetry_log_root()
    return {
        "telemetry_root": str(root),
        "scenarios": log_telemetry.list_log_scenarios(root),
        "default_scenario": log_telemetry.get_default_scenario(),
        "enabled": log_telemetry.is_voice_telemetry_enabled(),
    }


@router.get("/{sid}/telemetry/voice-queries", response_model=List[VoiceTelemetryQueryResponse])
def list_voice_queries(sid: str) -> List[dict]:
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return get_voice_telemetry_queries(sid)


@router.post(
    "/{sid}/telemetry/voice-query",
    response_model=VoiceTelemetryQueryResponse,
    status_code=201,
)
async def create_voice_query(sid: str, body: VoiceTelemetryQueryRequest) -> dict:
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    if not log_telemetry.is_voice_telemetry_enabled():
        raise HTTPException(
            status_code=503,
            detail="Voice telemetry queries are disabled (VOICE_TELEMETRY_ENABLED=false).",
        )

    query_id = f"vtq_{uuid.uuid4().hex[:8]}"
    await broadcast(
        sid,
        EVENT_TELEMETRY_QUERY_STARTED,
        {"id": query_id, "transcript": body.transcript.strip()},
    )

    try:
        result = await log_telemetry.answer_from_transcript(
            body.transcript,
            default_scenario=body.scenario,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Voice telemetry query failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {e}") from e

    record = {
        "id": query_id,
        "session_id": sid,
        "transcript": result["transcript"],
        "action": result["action"],
        "scenario": result["scenario"],
        "intent": result["intent"],
        "answer": result["answer"],
        "is_telemetry_query": result["is_telemetry_query"],
        "created_at": utcnow(),
    }
    add_voice_telemetry_query(record)
    await broadcast(sid, EVENT_TELEMETRY_QUERY_DONE, record)
    return record
