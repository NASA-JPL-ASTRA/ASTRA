"""
STT Task API Routes (Session-Scoped)
Manages the lifecycle of speech-to-text transcription tasks.

Based on sponsor-approved "pause-based chunk" workflow (Week 6):
  1. Frontend detects audio pause → uploads chunk via POST /stt/upload
  2. Backend creates STT task, forwards to Whisper API with callback
  3. Whisper completes → POSTs to Backend callback
  4. Backend updates STT task, creates Note, broadcasts via WebSocket

Endpoints:
- POST /api/sessions/{sid}/stt/upload        - Upload audio, trigger Whisper (integrated)
- POST /api/sessions/{sid}/stt/tasks        - Register new STT task (manual)
- GET  /api/sessions/{sid}/stt/tasks        - List all tasks for session
- GET  /api/sessions/{sid}/stt/tasks/{tid}   - Get task status
- PUT  /api/sessions/{sid}/stt/tasks/{tid}   - Update task (done/failed)
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

logger = logging.getLogger(__name__)

from app.schemas import STTTaskCreate, STTTaskUpdate, STTTaskResponse
from app.database import stt_tasks_db, get_session, get_stt_tasks_by_session
from app.ws_manager import (
    broadcast,
    broadcast_error,
    EVENT_STT_TASK_CREATED,
    EVENT_STT_TASK_DONE,
)

router = APIRouter()
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://127.0.0.1:8001")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/{sid}/stt/upload")
async def stt_upload(
    sid: str,
    file: UploadFile = File(..., description="Audio file (WAV preferred)"),
    audio_chunk_id: str = Form(default="chunk"),
    duration_seconds: float = Form(default=0),
):
    """
    Receive audio from Frontend, forward to Whisper API.
    Creates STT task and registers callback for when Whisper completes.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    task_id = f"stt_{uuid.uuid4().hex[:8]}"
    now = utcnow()
    new_task = {
        "id": task_id,
        "session_id": sid,
        "audio_chunk_id": audio_chunk_id,
        "duration_seconds": duration_seconds,
        "status": "pending",
        "transcript": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    stt_tasks_db[task_id] = new_task

    await broadcast(sid, EVENT_STT_TASK_CREATED, new_task)

    base = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    callback_params = urlencode({"session_id": sid, "stt_task_id": task_id})
    callback_url = f"{base}/api/internal/whisper-callback?{callback_params}"

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        whisper_base = WHISPER_API_URL.rstrip("/")
        create_url = f"{whisper_base}/api/whisper/tasks/create"

        params = {
            "task_type": "transcribe",
            "language": "en",  # 仅英语，避免其他语言污染
            "priority": "high",
            "no_speech_threshold": "0.4",  # 0.8 太高会过滤掉正常语音，改为 0.4
            "condition_on_previous_text": "false",
            "hallucination_silence_threshold": "0.5",
            "vad_filter": "false",  # 关闭 VAD，避免安静/低音量音频被全部过滤导致空结果
            "callback_url": callback_url,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                with open(tmp_path, "rb") as fh:
                    files = {"file_upload": (file.filename or "audio.wav", fh, "audio/wav")}
                    resp = await client.post(create_url, params=params, files=files)
        except httpx.ConnectError as e:
            logger.error(f"Whisper API connection failed: {e}")
            err_msg = f"Whisper API 未启动或不可达 ({WHISPER_API_URL})"
            new_task["status"] = "failed"
            new_task["error"] = err_msg
            new_task["updated_at"] = utcnow()
            await broadcast_error(sid, err_msg, source="stt")
            raise HTTPException(status_code=503, detail=err_msg)
        except Exception as e:
            logger.exception("Whisper API request failed")
            raise HTTPException(status_code=503, detail=str(e))

        if resp.status_code != 200:
            err_msg = resp.text or f"Whisper API error {resp.status_code}"
            logger.error("Whisper API returned %s: %s", resp.status_code, err_msg)
            new_task["status"] = "failed"
            new_task["error"] = err_msg
            new_task["updated_at"] = utcnow()
            await broadcast_error(sid, err_msg, source="stt")
            return {"id": task_id, "status": "failed", "error": err_msg}

        return new_task
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


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
    elif update.status == "failed":
        error_msg = update.error or "STT transcription failed"
        await broadcast_error(sid, error_msg, source="stt")

    return task
