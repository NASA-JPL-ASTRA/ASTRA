"""
Voice telemetry API backed by InfluxDB telemetry.

Endpoints:
- GET  /api/sessions/telemetry/log-scenarios
- GET  /api/sessions/{sid}/telemetry/voice-queries
- POST /api/sessions/{sid}/telemetry/voice-query
- POST /api/sessions/{sid}/telemetry/voice-query/audio
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import (
    add_voice_telemetry_query,
    get_session,
    get_voice_telemetry_queries,
)
from app.services import log_telemetry
from app.services.openai_stt import (
    SUPPORTED_STT_MODELS,
    OpenAIStreamingTranscriptionService,
)
from app.ws_manager import (
    EVENT_TELEMETRY_QUERY_DONE,
    EVENT_TELEMETRY_QUERY_STARTED,
    broadcast,
)

logger = logging.getLogger(__name__)

router = APIRouter()
stt_service = OpenAIStreamingTranscriptionService()


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


async def _transcribe_audio_file(
    *,
    file_name: str,
    file_content: bytes,
    content_type: str,
    model: str | None,
) -> str:
    selected_model = (model or stt_service.model).strip()
    if selected_model not in SUPPORTED_STT_MODELS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported STT model '{selected_model}'. "
                f"Supported models: {', '.join(sorted(SUPPORTED_STT_MODELS))}"
            ),
        )

    transcript = ""
    async for event in stt_service.stream_transcription(
        file_name=file_name,
        file_bytes=file_content,
        content_type=content_type,
        model=selected_model,
    ):
        if event.type == "transcript.text.delta" and event.delta:
            transcript += event.delta
        elif event.type == "transcript.text.done" and event.text:
            transcript = event.text

    return transcript.strip()


async def _create_voice_query_record(
    *,
    sid: str,
    transcript: str,
    scenario: str | None,
) -> dict:
    if not log_telemetry.is_voice_telemetry_enabled():
        raise HTTPException(
            status_code=503,
            detail="Voice telemetry queries are disabled (VOICE_TELEMETRY_ENABLED=false).",
        )

    query_id = f"vtq_{uuid.uuid4().hex[:8]}"
    stripped = transcript.strip()
    await broadcast(
        sid,
        EVENT_TELEMETRY_QUERY_STARTED,
        {"id": query_id, "transcript": stripped},
    )

    try:
        result = await log_telemetry.answer_from_transcript(
            stripped,
            default_scenario=scenario,
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

    return await _create_voice_query_record(
        sid=sid,
        transcript=body.transcript,
        scenario=body.scenario,
    )


@router.post(
    "/{sid}/telemetry/voice-query/audio",
    response_model=VoiceTelemetryQueryResponse,
    status_code=201,
)
async def create_voice_query_from_audio(
    sid: str,
    file: UploadFile = File(...),
    scenario: str | None = Form(None),
    model: str | None = Form(None),
) -> dict:
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty")

    try:
        transcript = await _transcribe_audio_file(
            file_name=file.filename or "telemetry-query.webm",
            file_content=file_content,
            content_type=file.content_type or "audio/webm",
            model=model,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Voice telemetry transcription failed")
        raise HTTPException(status_code=503, detail=f"Voice transcription failed: {e}") from e

    if not transcript:
        raise HTTPException(status_code=400, detail="No speech detected in voice query")

    return await _create_voice_query_record(
        sid=sid,
        transcript=transcript,
        scenario=scenario,
    )
