"""
Sessions API Routes
Manage test sessions

Endpoints:
- POST   /api/sessions           - Create new session
- GET    /api/sessions           - List all sessions
- GET    /api/sessions/{sid}     - Get specific session
- PATCH  /api/sessions/{sid}     - Update session metadata (e.g., status=ended)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List
import uuid

from app.schemas import SessionCreate, SessionUpdate, SessionResponse, SessionStatus
from app.database import sessions_db, get_session, count_notes_by_session, structure_notes_db
from app.ws_manager import EVENT_STRUCTURE_NOTE_UPDATED, broadcast

router = APIRouter()


def _generate_session_test1_telemetry_job(session_id: str, started_at: datetime) -> None:
    """Background: write test_1 mock logs aligned to session start; store path on session dict."""
    from app.database import sessions_db
    from app.services.session_telemetry_mock import generate_test1_telemetry_for_session

    path = generate_test1_telemetry_for_session(session_id, started_at)
    sess = sessions_db.get(session_id)
    if sess is not None and path:
        sess["telemetry_mock_test1_path"] = path


async def _finalize_structure_note_job(session_id: str) -> None:
    """Runs after session ends: fills test_summary and notifies WebSocket clients."""
    from app.services.structure_note_engine import finalize_session_structure_note

    finalize_session_structure_note(session_id)
    payload = structure_notes_db.get(session_id, {})
    await broadcast(session_id, EVENT_STRUCTURE_NOTE_UPDATED, payload)


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def serialize_session(session: dict) -> dict:
    """Attach computed fields so every session response shares one source of truth."""
    return {
        **session,
        "note_count": count_notes_by_session(session["id"]),
        "telemetry_mock_test1_path": session.get("telemetry_mock_test1_path"),
    }


@router.post("", response_model=SessionResponse)
def create_session(session: SessionCreate, background_tasks: BackgroundTasks):
    """
    Create new test session
    Called by: Frontend / System
    """
    session_id = f"sess_{uuid.uuid4().hex[:8]}"

    new_session = {
        "id": session_id,
        "name": session.name,
        "description": session.description,
        "status": SessionStatus.active,
        "started_at": utcnow(),
        "ended_at": None,
        "telemetry_mock_test1_path": None,
    }

    sessions_db[session_id] = new_session
    background_tasks.add_task(
        _generate_session_test1_telemetry_job,
        session_id,
        new_session["started_at"],
    )
    return serialize_session(new_session)


@router.get("", response_model=List[SessionResponse])
def list_sessions():
    """
    List all sessions, sorted newest first.
    Called by: Frontend
    """
    sessions = sorted(
        sessions_db.values(),
        key=lambda x: x["started_at"],
        reverse=True,
    )
    return [serialize_session(session) for session in sessions]


@router.get("/{sid}", response_model=SessionResponse)
def get_session_by_id(sid: str):
    """
    Get specific session.
    Called by: Frontend
    """
    session = get_session(sid)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return serialize_session(session)


@router.patch("/{sid}", response_model=SessionResponse)
def update_session(sid: str, update: SessionUpdate, background_tasks: BackgroundTasks):
    """
    Update session metadata (e.g., status=ended).
    Called by: Frontend / System
    """
    session = get_session(sid)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    if update.name is not None:
        session["name"] = update.name
    if update.description is not None:
        session["description"] = update.description
    if update.status is not None:
        session["status"] = update.status
        if update.status == SessionStatus.ended:
            session["ended_at"] = utcnow()
            background_tasks.add_task(_finalize_structure_note_job, sid)

    return serialize_session(session)
