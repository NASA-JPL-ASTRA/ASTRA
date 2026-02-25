"""
Telemetry API Routes (Session-Scoped)
Manage telemetry data ingestion and queries

Endpoints:
- POST /api/sessions/{sid}/telemetry           - Ingest telemetry data
- POST /api/sessions/{sid}/telemetry/batch     - Batch ingest
- GET  /api/sessions/{sid}/telemetry           - Query telemetry (filters: channel, from/to)
- GET  /api/sessions/{sid}/telemetry/latest    - Get latest value (e.g., ?channel=voltage)
- GET  /api/sessions/{sid}/telemetry/channels  - List available channels
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.schemas import TelemetryCreate, TelemetryBatchCreate, TelemetryResponse
from app.database import telemetry_db, get_session, get_telemetry_by_session

router = APIRouter()


def _to_aware(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware for safe comparison."""
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/{sid}/telemetry", response_model=TelemetryResponse)
def create_telemetry(sid: str, telemetry: TelemetryCreate):
    """
    Ingest telemetry data.
    Called by: Telemetry Source / AI Module

    Simple schema: timestamp, channel, value, unit
    Sponsor said: define your own simple schema, they will convert their data to match.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    telemetry_id = f"tel_{uuid.uuid4().hex[:8]}"
    new_telemetry = {
        "id": telemetry_id,
        "session_id": sid,
        "timestamp": _to_aware(telemetry.timestamp),
        "channel": telemetry.channel,
        "value": telemetry.value,
        "unit": telemetry.unit,
    }
    telemetry_db.append(new_telemetry)
    return new_telemetry


@router.post("/{sid}/telemetry/batch")
def create_telemetry_batch(sid: str, batch: TelemetryBatchCreate):
    """
    Batch ingest telemetry data.
    Called by: Telemetry Source
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    created_count = 0
    for telemetry in batch.data:
        telemetry_id = f"tel_{uuid.uuid4().hex[:8]}"
        telemetry_db.append({
            "id": telemetry_id,
            "session_id": sid,
            "timestamp": _to_aware(telemetry.timestamp),
            "channel": telemetry.channel,
            "value": telemetry.value,
            "unit": telemetry.unit,
        })
        created_count += 1

    return {"created": created_count}


@router.get("/{sid}/telemetry", response_model=List[TelemetryResponse])
def list_telemetry(
    sid: str,
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Filter from timestamp (ISO 8601)"),
    to_time: Optional[datetime] = Query(None, alias="to", description="Filter to timestamp (ISO 8601)"),
    limit: int = Query(1000, description="Max records to return"),
):
    """
    Query telemetry with optional filters.
    Called by: Frontend / AI Module
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    results = get_telemetry_by_session(sid)

    if channel:
        results = [t for t in results if t["channel"] == channel]
    if from_time:
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=timezone.utc)
        results = [t for t in results if _to_aware(t["timestamp"]) >= from_time]
    if to_time:
        if to_time.tzinfo is None:
            to_time = to_time.replace(tzinfo=timezone.utc)
        results = [t for t in results if _to_aware(t["timestamp"]) <= to_time]

    results.sort(key=lambda x: _to_aware(x["timestamp"]), reverse=True)
    return results[:limit]


@router.get("/{sid}/telemetry/latest", response_model=TelemetryResponse)
def get_latest_telemetry(
    sid: str,
    channel: str = Query(..., description="Channel name (required). Example: ?channel=voltage"),
):
    """
    Get latest value for a channel.
    Called by: AI/Data Module

    Used when operator says "ASTRA, log the voltage" —
    AI module calls this to get the current value and attach it to a note.
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    results = [t for t in get_telemetry_by_session(sid) if t["channel"] == channel]

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No telemetry found for channel: {channel}",
        )

    results.sort(key=lambda x: _to_aware(x["timestamp"]), reverse=True)
    return results[0]


@router.get("/{sid}/telemetry/channels")
def list_channels(sid: str):
    """
    List all unique channel names in this session.
    Called by: Frontend
    """
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")

    results = get_telemetry_by_session(sid)
    channels = sorted(set(t["channel"] for t in results))
    return {"channels": channels}
