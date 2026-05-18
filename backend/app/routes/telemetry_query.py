"""
AiSTRA Telemetry Query API (FastAPI)

Same behavior as telemetry/app.py (Flask): wraps influx_query + channel_search.

Public paths (with ``prefix="/api"`` on the router): ``/api/query/...``
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query

from app.services.influx_query import (
    get_channel_value,
    get_recent_events,
    query_channel_range,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _upstream_error(exc: Exception) -> HTTPException:
    logger.exception("Telemetry query failed")
    return HTTPException(
        status_code=503,
        detail=f"Telemetry backend unavailable: {exc}",
    )


def _channel_search_installed() -> bool:
    """TF-IDF search is optional; avoid importing sklearn at app startup."""
    return importlib.util.find_spec("sklearn") is not None


@router.get("/query", summary="Telemetry query API info")
def query_api_info() -> dict[str, Any]:
    return {
        "service": "AiSTRA Telemetry Query API",
        "endpoints": [
            "/api/query/channel",
            "/api/query/range",
            "/api/query/events",
            "/api/query/search",
        ],
        "legacy_flask_paths": ["/channel", "/range", "/events", "/search"],
        "channel_search_available": _channel_search_installed(),
        "note": "Use /api/query/* via the ASTRA backend (replaces standalone Flask on :5001). "
        "GET /api/query/search needs scikit-learn + numpy (see requirements.txt).",
    }


@router.get("/query/channel")
def channel(
    session: str = Query(..., description="Session id (Influx tag session_id)"),
    channel: str = Query(..., alias="name", description="Channel name"),
    at: float = Query(..., description="Unix time — last sample at or before this instant"),
) -> dict[str, Any]:
    sid = session.strip()
    ch = channel.strip()
    try:
        result = get_channel_value(session_id=sid, channel=ch, at_time=at)
    except Exception as e:
        raise _upstream_error(e) from e

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data found for channel '{ch}' before timestamp {at} "
                f"in session '{sid}'. "
                "Use the same Influx session_id as telemetry/ingestor.py and check "
                "INFLUX_URL / INFLUX_BUCKET in backend/.env (must match telemetry/query.py)."
            ),
        )
    return result


@router.get("/query/range")
def range_query(
    session: str = Query(...),
    channel: str = Query(..., alias="name", description="Channel name"),
    t0: float = Query(..., description="Window start (Unix)"),
    t1: float = Query(..., description="Window end (Unix)"),
) -> dict[str, Any]:
    if t0 >= t1:
        raise HTTPException(
            status_code=400,
            detail=f"t0 ({t0}) must be less than t1 ({t1})",
        )

    sid = session.strip()
    ch = channel.strip()
    try:
        result = query_channel_range(
            session_id=sid,
            channel=ch,
            start_time=t0,
            end_time=t1,
        )
    except Exception as e:
        raise _upstream_error(e) from e

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data found for channel '{ch}' in window [{t0}, {t1}] "
                f"in session '{sid}'"
            ),
        )
    return result


@router.get("/query/events", response_model=List[dict[str, Any]])
def events(
    session: str = Query(...),
    t0: float = Query(...),
    t1: float = Query(...),
    severity: str = Query("all"),
    limit: int = Query(20, ge=1, le=500),
) -> List[dict[str, Any]]:
    valid = {"all", "warning", "activity_hi", "activity_lo", "command"}
    if severity not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity '{severity}'. Must be one of: {', '.join(sorted(valid))}",
        )

    try:
        return get_recent_events(
            session_id=session.strip(),
            start_time=t0,
            end_time=t1,
            severity=severity,
            limit=limit,
        )
    except Exception as e:
        raise _upstream_error(e) from e


@router.get("/query/search", response_model=List[dict[str, Any]])
def search(
    q: str = Query(..., description="Natural language channel hint"),
    k: int = Query(3, ge=1, le=50, description="Number of results"),
) -> List[dict[str, Any]]:
    stripped = (q or "").strip()
    if not stripped:
        raise HTTPException(status_code=400, detail="Missing parameter: q")
    try:
        from app.services.channel_search import search_channel
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "Channel search needs scikit-learn and numpy. "
                "Install with: pip install -r requirements.txt "
                f"({e})"
            ),
        ) from e
    try:
        return search_channel(stripped, top_k=k)
    except Exception as e:
        raise _upstream_error(e) from e
