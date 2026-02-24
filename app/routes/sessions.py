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

from app.schemas import SessionCreate, SessionUpdate, SessionResponse, SessionStatus
from app.database import sessions_db, get_session

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
    return sessions


@router.get("/{sid}", response_model=SessionResponse)
def get_session_by_id(sid: str):
    """
    Get specific session.
    Called by: Frontend
    """
    session = get_session(sid)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return session


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
