"""
Structure Note API — one document per session (naive local timestamps, no timezone).

Endpoints:
- GET  /api/sessions/{sid}/structure-note              — fetch or create empty document
- POST /api/sessions/{sid}/structure-note/voice-chunk — merge one transcript chunk (LLM or fallback)
"""

from fastapi import APIRouter, HTTPException

from app.database import get_session
from app.schemas.structure_note import (
    StructureNoteDocument,
    VoiceChunkRequest,
    document_to_storage_dict,
)
from app.services.structure_note_engine import apply_voice_chunk, get_or_create_structure_note
from app.ws_manager import EVENT_STRUCTURE_NOTE_UPDATED, broadcast

router = APIRouter()


@router.get("/{sid}/structure-note", response_model=StructureNoteDocument)
def get_structure_note(sid: str):
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return get_or_create_structure_note(sid)


@router.post("/{sid}/structure-note/voice-chunk", response_model=StructureNoteDocument)
async def post_voice_chunk(sid: str, body: VoiceChunkRequest):
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    doc = apply_voice_chunk(
        sid,
        body.transcript.strip(),
        request_anomaly_capture=body.request_anomaly_capture,
    )
    await broadcast(sid, EVENT_STRUCTURE_NOTE_UPDATED, document_to_storage_dict(doc))
    return doc
