"""
WebSocket Manager
Centralized broadcast logic for all real-time events.
"""

import json
import logging
from fastapi.encoders import jsonable_encoder
from app.database import ws_connections

logger = logging.getLogger(__name__)

# ============ Event Type Constants ============
EVENT_NOTE_CREATED     = "note.created"
EVENT_NOTE_UPDATED     = "note.updated"
EVENT_NOTE_DELETED     = "note.deleted"

EVENT_STT_TASK_CREATED = "stt.task.created"
EVENT_STT_TASK_DONE    = "stt.task.done"
EVENT_STT_CHUNK_READY  = "transcript.chunk.ready"

EVENT_ERROR_OCCURRED   = "error.occurred"   # NEW


# ============ Broadcast ============

async def broadcast(session_id: str, event: str, data: dict):
    """Broadcast an event to all WebSocket clients connected to a session."""
    if session_id not in ws_connections:
        return

    payload = {
        "event": event,
        "session_id": session_id,
        "data": data,
    }
    message = json.dumps(jsonable_encoder(payload))

    dead_connections = []
    for ws in ws_connections[session_id]:
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.warning(f"WebSocket send failed for session {session_id}: {e}")
            dead_connections.append(ws)

    for ws in dead_connections:
        if ws in ws_connections[session_id]:
            ws_connections[session_id].remove(ws)
    if session_id in ws_connections and not ws_connections[session_id]:
        del ws_connections[session_id]


async def broadcast_error(session_id: str, message: str, source: str = "system"):   # NEW
    """Broadcast an error event to all clients in a session."""
    await broadcast(session_id, EVENT_ERROR_OCCURRED, {
        "message": message,
        "source": source,
    })
