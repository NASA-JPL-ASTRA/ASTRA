"""
STT Task API Routes (Session-Scoped)
Manages the lifecycle of speech-to-text transcription tasks.

Based on sponsor-approved "pause-based chunk" workflow (Week 6):
  1. Frontend detects audio pause → uploads chunk
  2. AI team calls POST /stt/tasks to register task (status: pending)
  3. AI team processes audio with Whisper
  4. AI team calls PUT /stt/tasks/{id} with transcript (status: done)
  5. Backend broadcasts stt.task.done → Frontend shows transcript

Endpoints:
- POST /api/sessions/{sid}/stt/tasks         - Register new STT task
- GET  /api/sessions/{sid}/stt/tasks         - List all tasks for session
- GET  /api/sessions/{sid}/stt/tasks/{tid}   - Get task status
- PUT  /api/sessions/{sid}/stt/tasks/{tid}   - Update task (done/failed)
"""

import logging
import time

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from app.schemas import STTTaskCreate, STTTaskUpdate, STTTaskResponse
from app.database import stt_tasks_db, notes_db, get_session, get_stt_tasks_by_session
from app.ws_manager import (
    broadcast,
    broadcast_error,
    EVENT_STT_TASK_CREATED,
    EVENT_STT_TASK_DONE,
    EVENT_NOTE_CREATED,
    EVENT_STT_CHUNK_READY,
    EVENT_STRUCTURE_NOTE_UPDATED,
)
from app.services.openai_stt import (
    SUPPORTED_STT_MODELS,
    OpenAIStreamingTranscriptionService,
)
from app.services.transcript_quality import transcript_qualifies_for_notes

logger = logging.getLogger(__name__)
router = APIRouter()

stt_service = OpenAIStreamingTranscriptionService()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _create_auto_note(sid: str, transcript: str) -> Optional[dict]:
    cleaned = transcript.strip()
    if not transcript_qualifies_for_notes(cleaned):
        return None

    note_id = f"note_{uuid.uuid4().hex[:8]}"
    now = utcnow()
    new_note = {
        "id": note_id,
        "session_id": sid,
        "timestamp": now,
        "speaker": None,
        "content": cleaned,
        "type": "observation",
        "tags": ["auto-transcription"],
        "telemetry_snapshot": None,
        "created_at": now,
        "updated_at": now,
    }
    notes_db[note_id] = new_note
    await broadcast(sid, EVENT_NOTE_CREATED, new_note)
    return new_note


async def _sync_structure_note_from_transcript(sid: str, transcript: str) -> None:
    """
    Merge transcript into the session structure note (detail + optional anomaly).
    Heuristic: common Chinese/English phrases imply user asked to log an issue.
    """
    from app.schemas.structure_note import document_to_storage_dict
    from app.services.structure_note_engine import apply_voice_chunk

    text = transcript.strip()
    if not transcript_qualifies_for_notes(text):
        return
    tl = text.lower()
    request_anomaly = any(m in text for m in ("記下來", "幫我記", "問題", "異常")) or any(
        m in tl
        for m in (
            "please log",
            "log this for me",
            "log this",
            "remember this",
            "anomaly",
            "knocking",
        )
    )
    doc = apply_voice_chunk(sid, text, request_anomaly_capture=request_anomaly)
    await broadcast(sid, EVENT_STRUCTURE_NOTE_UPDATED, document_to_storage_dict(doc))


async def _transcribe_uploaded_audio(
    *,
    sid: str,
    task: dict,
    file_name: str,
    file_content: bytes,
    content_type: str,
    model: str,
) -> None:
    transcript = ""

    try:
        async for event in stt_service.stream_transcription(
            file_name=file_name,
            file_bytes=file_content,
            content_type=content_type,
            model=model,
        ):
            if event.type == "transcript.text.delta" and event.delta:
                transcript += event.delta
                await broadcast(sid, EVENT_STT_CHUNK_READY, {
                    "id": task["id"],
                    "audio_chunk_id": task["audio_chunk_id"],
                    "delta": event.delta,
                    "transcript": transcript,
                    "is_final": False,
                })
            elif event.type == "transcript.text.done" and event.text:
                transcript = event.text

        task["status"] = "done"
        task["transcript"] = transcript.strip() or None
        task["error"] = None
        task["updated_at"] = utcnow()

        await broadcast(sid, EVENT_STT_TASK_DONE, task)

        if task["transcript"]:
            await _create_auto_note(sid, task["transcript"])
            await _sync_structure_note_from_transcript(sid, task["transcript"])
    except Exception as e:
        logger.exception("OpenAI transcription failed for task %s", task["id"])
        task["status"] = "failed"
        task["error"] = str(e)
        task["updated_at"] = utcnow()
        await broadcast_error(sid, f"OpenAI transcription failed: {e}", source="stt")


@router.post("/{sid}/stt/tasks", response_model=STTTaskResponse, status_code=201)
async def create_stt_task(sid: str, task: STTTaskCreate):
    """
    Register a new STT task.
    Called by: AI/Data team when a new audio chunk is ready.

    Broadcasts: stt.task.created
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    task_id = f"stt_{uuid.uuid4().hex[:8]}"
    now = utcnow()
    new_task = {
        "id":               task_id,
        "session_id":       sid,
        "audio_chunk_id":   task.audio_chunk_id,
        "duration_seconds": task.duration_seconds,
        "status":           "pending",
        "transcript":       None,
        "error":            None,
        "created_at":       now,
        "updated_at":       now,
    }
    stt_tasks_db[task_id] = new_task

    await broadcast(sid, EVENT_STT_TASK_CREATED, new_task)
    return new_task


@router.get("/{sid}/stt/tasks", response_model=List[STTTaskResponse])
def list_stt_tasks(sid: str):
    """
    List all STT tasks for a session, newest first.
    Called by: Frontend (to show processing history)
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    tasks = get_stt_tasks_by_session(sid)
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return tasks


@router.get("/{sid}/stt/tasks/{tid}", response_model=STTTaskResponse)
def get_stt_task(sid: str, tid: str):
    """
    Get a single STT task by ID.
    Called by: Frontend / AI team (to poll status)
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    task = stt_tasks_db.get(tid)
    if not task or task["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"STT task {tid} not found")

    return task


@router.put("/{sid}/stt/tasks/{tid}", response_model=STTTaskResponse)
async def update_stt_task(sid: str, tid: str, update: STTTaskUpdate):
    """
    Update STT task status (done or failed).
    Called by: AI/Data team when Whisper finishes processing.

    Broadcasts:
      - stt.task.done       if status == done
      - error.occurred      if status == failed
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    task = stt_tasks_db.get(tid)
    if not task or task["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"STT task {tid} not found")

    task["status"]     = update.status
    task["transcript"] = update.transcript
    task["error"]      = update.error
    task["updated_at"] = utcnow()

    if update.status == "done":
        await broadcast(sid, EVENT_STT_TASK_DONE, task)
        tx = (update.transcript or "").strip()
        if tx:
            await _sync_structure_note_from_transcript(sid, tx)
    elif update.status == "failed":
        error_msg = update.error or "STT transcription failed"
        await broadcast_error(sid, error_msg, source="stt")

    return task


# ─────────────────────────────────────────────────────────────
# Upload audio → transcribe with OpenAI and broadcast incremental output
# ─────────────────────────────────────────────────────────────

@router.post("/{sid}/stt/upload")
async def upload_audio(
    sid: str,
    file: UploadFile = File(...),
    audio_chunk_id: Optional[str] = Form(None),
    duration_seconds: Optional[float] = Form(None),
    model: Optional[str] = Form(None),
):
    """
    Receive an audio file from the frontend, transcribe it with OpenAI,
    and stream transcript deltas back through the session WebSocket.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    selected_model = (model or stt_service.model).strip()
    if selected_model not in SUPPORTED_STT_MODELS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported STT model '{selected_model}'. "
                f"Supported models: {', '.join(sorted(SUPPORTED_STT_MODELS))}"
            ),
        )

    task_id = f"stt_{uuid.uuid4().hex[:8]}"
    now = utcnow()
    chunk_id = audio_chunk_id or f"chunk_{int(time.time() * 1000)}"

    new_task = {
        "id":               task_id,
        "session_id":       sid,
        "audio_chunk_id":   chunk_id,
        "duration_seconds": duration_seconds,
        "model":            selected_model,
        "status":           "pending",
        "transcript":       None,
        "error":            None,
        "created_at":       now,
        "updated_at":       now,
    }
    stt_tasks_db[task_id] = new_task
    await broadcast(sid, EVENT_STT_TASK_CREATED, new_task)

    file_content = await file.read()
    try:
        await _transcribe_uploaded_audio(
            sid=sid,
            task=new_task,
            file_name=file.filename or "chunk.wav",
            file_content=file_content,
            content_type=file.content_type or "audio/wav",
            model=selected_model,
        )
    except Exception as e:
        logger.error("STT upload failed for task %s: %s", task_id, e)
        new_task["status"] = "failed"
        new_task["error"] = str(e)
        new_task["updated_at"] = utcnow()
        await broadcast_error(sid, f"STT upload failed: {e}", source="stt")

    return new_task
