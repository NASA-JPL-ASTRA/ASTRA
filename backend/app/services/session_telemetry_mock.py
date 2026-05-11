"""
When a new session is created, generate Test 1 straight-line mock telemetry
(channel.log / event.log) under backend/data/session_telemetry/<session_id>/,
with the synthetic timeline anchored so the last sample matches session start (UTC).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_TOOLS_GEN = _REPO_ROOT / "tools" / "telemetry-generator"


def _as_utc_epoch_seconds(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).timestamp()


def generate_test1_telemetry_for_session(session_id: str, session_started_at: datetime) -> Optional[str]:
    """
    Run scenario_1_straight_line_bumps into:
      backend/data/session_telemetry/<session_id>/test_1_straight_line/

    Returns a repo-relative path string for UI/docs, or None on failure.
    """
    if not _TOOLS_GEN.is_dir():
        logger.error("telemetry-generator not found: %s", _TOOLS_GEN)
        return None

    out_dir = _BACKEND_ROOT / "data" / "session_telemetry" / session_id / "test_1_straight_line"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error("Could not create telemetry mock dir %s: %s", out_dir, e)
        return None

    align = _as_utc_epoch_seconds(session_started_at)

    inserted = str(_TOOLS_GEN.resolve())
    old_path = sys.path[:]
    try:
        if inserted not in sys.path:
            sys.path.insert(0, inserted)
        from scenarios import scenario_1_straight_line_bumps

        scenario_1_straight_line_bumps(str(out_dir.resolve()), align_flush_unix=align)
    except Exception:
        logger.exception("Test 1 telemetry generation failed for session %s", session_id)
        return None
    finally:
        sys.path[:] = old_path

    return f"backend/data/session_telemetry/{session_id}/test_1_straight_line"
