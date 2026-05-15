"""
Structure Note API — one document per session (naive local timestamps, no timezone).

Endpoints:
- GET  /api/sessions/{sid}/structure-note              — fetch or create empty document
- POST /api/sessions/{sid}/structure-note/voice-chunk — merge one transcript chunk (LLM or fallback)
"""

from fastapi import APIRouter, HTTPException

from app.database import get_session, structure_notes_db
from app.schemas.structure_note import (
    StructureNoteDocument,
    TestSummaryAutoUpdateRequest,
    TestSummaryAutoUpdateResponse,
    TestSummaryStatus,
    TestSummaryUpdateRequest,
    VoiceChunkRequest,
    document_to_storage_dict,
)
from app.services.structure_note_engine import (
    apply_voice_chunk,
    auto_update_test_summary,
    get_or_create_structure_note,
    utc_iso_timestamp,
)
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


@router.put("/{sid}/structure-note/test-summary", response_model=StructureNoteDocument)
async def update_test_summary(sid: str, body: TestSummaryUpdateRequest):
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    doc = get_or_create_structure_note(sid)
    timestamp = utc_iso_timestamp()
    doc.test_summary.status = TestSummaryStatus.ready
    doc.test_summary.content_markdown = body.content_markdown.strip()
    doc.test_summary.generated_at = timestamp
    doc.test_summary.error = None
    doc.updated_at = timestamp

    payload = document_to_storage_dict(doc)
    structure_notes_db[sid] = payload
    await broadcast(sid, EVENT_STRUCTURE_NOTE_UPDATED, payload)
    return doc


@router.post(
    "/{sid}/structure-note/test-summary/auto-update",
    response_model=TestSummaryAutoUpdateResponse,
)
async def auto_update_test_summary_route(sid: str, body: TestSummaryAutoUpdateRequest):
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    try:
        doc, last_note_id, processed_note_count = auto_update_test_summary(
            sid,
            body.manual_summary,
            since_note_id=body.since_note_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = document_to_storage_dict(doc)
    structure_notes_db[sid] = payload
    await broadcast(sid, EVENT_STRUCTURE_NOTE_UPDATED, payload)
    return TestSummaryAutoUpdateResponse(
        document=doc,
        last_note_id=last_note_id,
        processed_note_count=processed_note_count,
    )
