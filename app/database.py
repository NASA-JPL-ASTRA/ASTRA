"""
In-Memory Database
For development/testing - will be replaced with PostgreSQL later
"""

from typing import Dict, List, Any
from datetime import datetime

# ============ In-Memory Storage ============

sessions_db:   Dict[str, dict] = {}
notes_db:      Dict[str, dict] = {}
telemetry_db:  List[dict]      = []
stt_tasks_db:  Dict[str, dict] = {}   # NEW: STT task storage

# WebSocket connections: { session_id: [websocket1, ...] }
ws_connections: Dict[str, List[Any]] = {}


# ============ Helper Functions ============

def get_session(session_id: str) -> dict | None:
    return sessions_db.get(session_id)


def get_notes_by_session(session_id: str) -> List[dict]:
    return [n for n in notes_db.values() if n["session_id"] == session_id]


def get_telemetry_by_session(session_id: str) -> List[dict]:
    return [t for t in telemetry_db if t["session_id"] == session_id]


def get_stt_tasks_by_session(session_id: str) -> List[dict]:   # NEW
    return [t for t in stt_tasks_db.values() if t["session_id"] == session_id]
