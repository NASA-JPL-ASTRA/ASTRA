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

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from typing import List
import uuid

from app.schemas import STTTaskCreate, STTTaskUpdate, STTTaskResponse
from app.database import stt_tasks_db, get_session, get_stt_tasks_by_session
from app.ws_manager import (
    broadcast, broadcast_error,
    EVENT_STT_TASK_CREATED, EVENT_STT_TASK_DONE,
)

router = APIRouter()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
