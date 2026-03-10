"""
Sessions API Routes
Manage test sessions

Endpoints:
- POST   /api/sessions           - Create new session
- GET    /api/sessions           - List all sessions
- GET    /api/sessions/{sid}     - Get specific session
- PATCH  /api/sessions/{sid}     - Update session metadata (e.g., status=ended)
"""

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
import uuid

from app.schemas import SessionCreate, SessionUpdate, SessionResponse, SessionStatus, SessionWithNotesResponse
from app.database import sessions_db, get_session, get_notes_by_session

router = APIRouter()


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@router.post("", response_model=SessionResponse)
def create_session(session: SessionCreate):
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
    }

    sessions_db[session_id] = new_session
    return new_session


@router.get("", response_model=List[SessionWithNotesResponse])
def list_sessions():
    """
    List all sessions with notes (transcriptions), sorted newest first.
    Called by: Frontend
    """
    sessions = sorted(
        sessions_db.values(),
        key=lambda x: x["started_at"],
        reverse=True,
    )
    result = []
    for s in sessions:
        notes = get_notes_by_session(s["id"])
        notes_sorted = sorted(notes, key=lambda n: n["timestamp"])
        result.append({**s, "notes": notes_sorted})
    return result


@router.get("/{sid}", response_model=SessionWithNotesResponse)
def get_session_by_id(sid: str):
    """
    Get specific session with notes (transcriptions).
    Called by: Frontend
    """
    session = get_session(sid)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    notes = get_notes_by_session(sid)
    notes_sorted = sorted(notes, key=lambda n: n["timestamp"])
    return {**session, "notes": notes_sorted}


@router.patch("/{sid}", response_model=SessionResponse)
def update_session(sid: str, update: SessionUpdate):
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

    return session
