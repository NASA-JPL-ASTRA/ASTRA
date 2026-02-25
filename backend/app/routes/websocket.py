"""
WebSocket Routes
Real-time note updates broadcast

Endpoint:
- WS /ws/sessions/{sid} - Subscribe to note updates for a session

Events broadcast (see ws_manager.py for full event type list):
- note.created  - New note added
- note.updated  - Note was edited
- note.deleted  - Note was removed

Sponsor requirement: Real-time collaborative interface where AI writes notes
and operators can see them appear in real-time.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import ws_connections, get_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/{sid}")
async def websocket_endpoint(websocket: WebSocket, sid: str):
    """
    WebSocket endpoint for real-time note updates.
    Called by: Frontend (subscribe)

    Usage:
    1. Frontend connects to /ws/sessions/{sid}
    2. Backend broadcasts events when notes change
    3. Frontend updates UI in real-time
    """
    session = get_session(sid)
    if not session:
        await websocket.close(code=4004, reason=f"Session {sid} not found")
        return

    await websocket.accept()

    if sid not in ws_connections:
        ws_connections[sid] = []
    ws_connections[sid].append(websocket)

    try:
        await websocket.send_text(json.dumps({
            "event": "connected",
            "session_id": sid,
            "data": {"message": f"Connected to session {sid}"},
        }))

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={sid}")
    except Exception as e:
        logger.warning(f"WebSocket error: session={sid}, error={e}")
    finally:
        if sid in ws_connections and websocket in ws_connections[sid]:
            ws_connections[sid].remove(websocket)
            if not ws_connections[sid]:
                del ws_connections[sid]
