"""
Telemetry API Routes (Session-Scoped)

GET endpoints read from InfluxDB (Yuyang's Docker instance).
POST endpoints write to in-memory (existing behavior).

Endpoints:
- POST  /{sid}/telemetry           - Ingest single data point
- POST  /{sid}/telemetry/batch     - Batch ingest
- GET   /{sid}/telemetry           - Query (filters: channel, from/to)
- GET   /{sid}/telemetry/latest    - Latest value for a channel
- GET   /{sid}/telemetry/channels  - List available channels
- GET   /{sid}/telemetry/summary   - Per-channel stats (min/max/latest)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from app.schemas import TelemetryCreate, TelemetryBatchCreate, TelemetryResponse
from app.database import telemetry_db, get_session, get_telemetry_by_session
from app import influx

router = APIRouter()


def _to_aware(dt: datetime) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── POST endpoints (write to in-memory, unchanged) ──────────────────────────

@router.post("/{sid}/telemetry", response_model=TelemetryResponse)
def create_telemetry(sid: str, telemetry: TelemetryCreate):
    """Ingest telemetry data. Called by: Telemetry Source / AI Module"""
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
    """Batch ingest telemetry data. Called by: Telemetry Source"""
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


# ── GET endpoints (read from InfluxDB) ──────────────────────────────────────

@router.get("/{sid}/telemetry", response_model=List[TelemetryResponse])
def list_telemetry(
    sid: str,
    channel: Optional[str] = Query(None),
    from_time: Optional[datetime] = Query(None, alias="from"),
    to_time: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(1000),
):
    """Query telemetry with optional filters. Called by: Frontend / AI Module"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return influx.query_range(sid, channel, from_time, to_time, limit)


@router.get("/{sid}/telemetry/latest", response_model=TelemetryResponse)
def get_latest_telemetry(
    sid: str,
    channel: str = Query(..., description="Channel name"),
):
    """Get latest value for a channel. Called by: AI/Data Module"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    result = influx.get_latest(sid, channel)
    if not result:
        raise HTTPException(status_code=404, detail=f"No telemetry for channel: {channel}")
    return result


@router.get("/{sid}/telemetry/channels")
def list_channels(sid: str):
    """List all unique channel names. Called by: Frontend"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return {"channels": influx.get_channels(sid)}


@router.get("/{sid}/telemetry/summary")
def telemetry_summary(sid: str):
    """Per-channel summary stats. Called by: Frontend / AI Module"""
    if not get_session(sid):
        raise HTTPException(status_code=404, detail=f"Session {sid} not found")
    return influx.get_summary(sid)
