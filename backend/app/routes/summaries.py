"""
Summary assistant API routes.
"""

from fastapi import APIRouter, HTTPException

from app.database import get_notes_by_session, get_session
from app.schemas import SummaryChatRequest, SummaryChatResponse
from app.services.summary_ai import chat_about_summary

router = APIRouter()


@router.post("/{sid}/summary/chat", response_model=SummaryChatResponse)
async def chat_with_summary_assistant(sid: str, request: SummaryChatRequest):
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    notes = get_notes_by_session(sid)
    result = await chat_about_summary(
        notes=notes,
        prompt=request.prompt,
        title=request.title,
        summary=request.summary,
        manual_summary=request.manual_summary,
        model=request.model,
        messages=[message.model_dump() for message in request.messages],
    )
    return result
