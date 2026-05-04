"""
Notes API Routes (Session-Scoped)
Manage AI-generated and operator-edited notes

Note types (sponsor wk14):
- detail:  real-time play-by-play, distilled from operator audio
- anomaly: operator-triggered issues, supports append over time
- summary: LLM generates once at session end

Endpoints:
- POST   /api/sessions/{sid}/notes           - Create note (AI module sends with type)
- GET    /api/sessions/{sid}/notes           - List notes (filterable by type, speaker, time)
- GET    /api/sessions/{sid}/notes/export    - Export notes grouped by type
- GET    /api/sessions/{sid}/notes/{id}      - Get specific note
- PUT    /api/sessions/{sid}/notes/{id}      - Edit note (operator correction, full replace)
- PATCH  /api/sessions/{sid}/notes/{id}      - Append to note (AI module appends to anomaly)
- DELETE /api/sessions/{sid}/notes/{id}      - Delete note
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import json

from app.schemas import NoteCreate, NoteUpdate, NoteAppend, NoteResponse, NoteType
from app.database import notes_db, get_session, get_notes_by_session
from app.ws_manager import (
    broadcast,
    EVENT_NOTE_CREATED, EVENT_NOTE_UPDATED, EVENT_NOTE_APPENDED, EVENT_NOTE_DELETED,
)

router = APIRouter()


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _to_aware(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware for safe comparison."""
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ─────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────

@router.post("/{sid}/notes", response_model=NoteResponse)
async def create_note(sid: str, note: NoteCreate):
    """
    Create note — AI module sends with `type` field to classify.

    Called by: AI/Data Module
    - type=detail:  LLM distilled a new play-by-play bullet
    - type=anomaly: operator said "this is a new anomaly"
    - type=summary: LLM generated session summary at end

    After storing, broadcasts note.created to all WebSocket clients.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    note_id = f"note_{uuid.uuid4().hex[:8]}"
    now = utcnow()

    new_note = {
        "id": note_id,
        "session_id": sid,
        "timestamp": _to_aware(note.timestamp),
        "speaker": note.speaker,
        "content": note.content,
        "type": note.type,
        "tags": note.tags,
        "telemetry_snapshot": note.telemetry_snapshot,
        "created_at": now,
        "updated_at": now,
    }

    notes_db[note_id] = new_note
    await broadcast(sid, EVENT_NOTE_CREATED, new_note)
    return new_note


# ─────────────────────────────────────────────────
# LIST + FILTER
# ─────────────────────────────────────────────────

@router.get("/{sid}/notes", response_model=List[NoteResponse])
def list_notes(
    sid: str,
    speaker: Optional[str] = Query(None, description="Filter by speaker"),
    type: Optional[NoteType] = Query(None, description="Filter by note type: detail | anomaly | summary"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Filter from timestamp (ISO 8601)"),
    to_time: Optional[datetime] = Query(None, alias="to", description="Filter to timestamp (ISO 8601)"),
):
    """
    List notes for session, sorted by timestamp ascending.
    Called by: Frontend

    Filter examples:
      ?type=anomaly          — show only anomalies
      ?type=detail&from=...  — play-by-play after a certain time
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    notes = get_notes_by_session(sid)

    if speaker:
        notes = [n for n in notes if n["speaker"] == speaker]
    if type:
        notes = [n for n in notes if n["type"] == type]
    if from_time:
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=timezone.utc)
        notes = [n for n in notes if _to_aware(n["timestamp"]) >= from_time]
    if to_time:
        if to_time.tzinfo is None:
            to_time = to_time.replace(tzinfo=timezone.utc)
        notes = [n for n in notes if _to_aware(n["timestamp"]) <= to_time]

    notes.sort(key=lambda x: _to_aware(x["timestamp"]))
    return notes


# ─────────────────────────────────────────────────
# EXPORT (grouped by type per sponsor wk14)
# ─────────────────────────────────────────────────

@router.get("/{sid}/notes/export", response_class=PlainTextResponse)
def export_notes(
    sid: str,
    format: str = Query("markdown", description="Export format: markdown | json"),
):
    """
    Export notes grouped by type: Summary → Anomalies → Detailed Notes.
    Called by: Frontend

    Sponsor requirement: ability to copy/paste notes into other systems.
    """
    session = get_session(sid)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    notes = get_notes_by_session(sid)
    notes.sort(key=lambda x: _to_aware(x["timestamp"]))

    summaries = [n for n in notes if n["type"] == NoteType.summary]
    anomalies = [n for n in notes if n["type"] == NoteType.anomaly]
    details   = [n for n in notes if n["type"] == NoteType.detail]

    if format == "json":
        export_data = {
            "session_id": sid,
            "session_name": session["name"],
            "exported_at": utcnow().isoformat(),
            "summary": summaries,
            "anomalies": anomalies,
            "detailed_notes": details,
        }
        return PlainTextResponse(
            content=json.dumps(export_data, indent=2, default=str),
            media_type="application/json",
        )

    # ── Markdown export ──
    lines = [
        f"# {session['name']}",
        "",
        f"**Session ID:** {sid}",
        f"**Started:** {session['started_at']}",
        f"**Status:** {session['status']}",
        "",
    ]

    # Summary section
    if summaries:
        lines += ["---", "", "## Test Summary", ""]
        for note in summaries:
            lines.append(note["content"])
            lines.append("")

    # Anomalies section
    if anomalies:
        lines += ["---", "", "## Anomalies", ""]
        for i, note in enumerate(anomalies, 1):
            ts = note["timestamp"]
            time_str = ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(ts)
            lines.append(f"### Anomaly #{i} [{time_str}]")
            lines.append("")
            lines.append(note["content"])
            lines.append("")
            if note.get("tags"):
                lines.append(f"*Tags: {', '.join(note['tags'])}*")
                lines.append("")

    # Detailed notes section
    if details:
        lines += ["---", "", "## Detailed Notes", ""]
        for note in details:
            ts = note["timestamp"]
            time_str = ts.strftime("%H:%M:%S") if hasattr(ts, "strftime") else str(ts)
            speaker = note["speaker"] or "System"

            lines.append(f"- **[{time_str}] {speaker}:** {note['content']}")
            if note.get("telemetry_snapshot"):
                snap = ", ".join(f"{k}={v}" for k, v in note["telemetry_snapshot"].items())
                lines.append(f"  - Telemetry: {snap}")

    lines.append("")
    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/markdown",
    )


# ─────────────────────────────────────────────────
# GET SINGLE
# ─────────────────────────────────────────────────

@router.get("/{sid}/notes/{note_id}", response_model=NoteResponse)
def get_note(sid: str, note_id: str):
    """Get specific note. Called by: Frontend"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    note = notes_db.get(note_id)
    if not note or note["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found in session {sid}")

    return note


# ─────────────────────────────────────────────────
# UPDATE (full field replace — operator correction)
# ─────────────────────────────────────────────────

@router.put("/{sid}/notes/{note_id}", response_model=NoteResponse)
async def update_note(sid: str, note_id: str, update: NoteUpdate):
    """
    Edit note (operator correction) — replaces field values.
    Called by: Frontend

    Sponsor requirement: operators must be able to edit AI-generated notes
    to build trust in the system.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    note = notes_db.get(note_id)
    if not note or note["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found in session {sid}")

    if update.content is not None:
        note["content"] = update.content
    if update.speaker is not None:
        note["speaker"] = update.speaker
    if update.type is not None:
        note["type"] = update.type
    if update.tags is not None:
        note["tags"] = update.tags

    note["updated_at"] = utcnow()

    await broadcast(sid, EVENT_NOTE_UPDATED, note)
    return note


# ─────────────────────────────────────────────────
# APPEND (add content — AI module appends to anomaly)
# ─────────────────────────────────────────────────

@router.patch("/{sid}/notes/{note_id}", response_model=NoteResponse)
async def append_to_note(sid: str, note_id: str, body: NoteAppend):
    """
    Append content to an existing note — used for anomaly updates.
    Called by: AI/Data Module

    Use case: Operator notices motor noise at 10:00. LLM creates anomaly note.
    At 11:30 same noise recurs. LLM appends new observation to the same note
    instead of creating a duplicate.

    The append_content is added on a new line with timestamp prefix.
    If telemetry_snapshot is provided, it is merged into the existing snapshot.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    note = notes_db.get(note_id)
    if not note or note["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found in session {sid}")

    # Build the appended line with timestamp
    append_ts = body.timestamp or utcnow()
    if append_ts.tzinfo is None:
        append_ts = append_ts.replace(tzinfo=timezone.utc)
    time_str = append_ts.strftime("%H:%M:%S")
    append_line = f"\n[{time_str}] {body.append_content}"

    note["content"] += append_line
    note["updated_at"] = utcnow()

    # Merge telemetry snapshot if provided
    if body.telemetry_snapshot:
        if note["telemetry_snapshot"] is None:
            note["telemetry_snapshot"] = {}
        note["telemetry_snapshot"].update(body.telemetry_snapshot)

    await broadcast(sid, EVENT_NOTE_APPENDED, note)
    return note


# ─────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────

@router.delete("/{sid}/notes/{note_id}")
async def delete_note(sid: str, note_id: str):
    """Delete note. Called by: Frontend"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    note = notes_db.get(note_id)
    if not note or note["session_id"] != sid:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found in session {sid}")

    del notes_db[note_id]
    await broadcast(sid, EVENT_NOTE_DELETED, {"id": note_id})
    return {"message": f"Note {note_id} deleted"}
