"""
Internal API Routes (called by Whisper API callback, not by Frontend)
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Body

from app.database import stt_tasks_db, notes_db

logger = logging.getLogger(__name__)
from app.ws_manager import (
    broadcast,
    broadcast_error,
    EVENT_STT_TASK_DONE,
    EVENT_NOTE_CREATED,
)

router = APIRouter()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_confidence_from_segments(segments: list) -> float | None:
    """
    Compute overall confidence from Whisper segments (avg_logprob, no_speech_prob).
    Formula: per-segment conf = (1 - no_speech_prob) * exp(avg_logprob)
    Returns None if no usable segments; caller should fallback to default (e.g. 0.9).
    """
    if not segments:
        return None
    confs = []
    for s in segments:
        if not isinstance(s, dict):
            continue
        no_speech = s.get("no_speech_prob")
        avg_logprob = s.get("avg_logprob")
        if no_speech is None and avg_logprob is None:
            continue
        seg_conf = 1.0
        if no_speech is not None:
            seg_conf *= 1.0 - float(no_speech)
        if avg_logprob is not None:
            seg_conf *= math.exp(float(avg_logprob))
        confs.append(seg_conf)
    if not confs:
        return None
    avg = sum(confs) / len(confs)
    return min(0.99, max(0.01, avg))


@router.post("/whisper-callback")
async def whisper_callback(
    session_id: str = Query(..., alias="session_id"),
    stt_task_id: str = Query(..., alias="stt_task_id"),
    body: dict = Body(default_factory=dict),
):
    """
    Called by Whisper API when transcription completes.
    Updates STT task and creates Note if transcript is valid.
    """
    task = stt_tasks_db.get(stt_task_id)
    if not task or task["session_id"] != session_id:
        # 任务不存在（如 Backend 重启后遗留的 Whisper 任务回调）：记录并忽略，返回 200 避免 Whisper 重试
        logger.warning("Ignoring stale callback: stt_task_id=%s session_id=%s (task not in db or session mismatch)",
                       stt_task_id, session_id)
        return {"ok": True, "ignored": "stale"}

    status = body.get("status")
    if status == "failed":
        task["status"] = "failed"
        task["error"] = body.get("error_message") or "Transcription failed"
        task["updated_at"] = utcnow()
        await broadcast_error(
            session_id,
            task["error"],
            source="stt",
        )
        return {"ok": True}

    result = body.get("result") or {}
    text = (result.get("text") or "").strip()

    # Debug: 若主路径无 text，打印结构便于排查
    if not text and result:
        logger.debug(
            "whisper-callback: result keys=%s has_text=%s",
            list(result.keys()) if result else [],
            "text" in result,
        )

    # Fallback: Whisper API 可能将 text 放在不同位置，或需从 segments 拼接
    if not text and result.get("segments"):
        segments = result.get("segments") or []
        text = " ".join(
            (s.get("text") or "").strip()
            for s in segments
            if isinstance(s, dict) and s.get("text")
        ).strip()
    filtered = result.get("filtered", False)

    # 从 segments 计算置信度（avg_logprob, no_speech_prob）
    segments = result.get("segments") or []
    confidence = compute_confidence_from_segments(segments)
    task["confidence"] = round(confidence, 2) if confidence is not None else 0.9

    # 调试：确认 Whisper 回调中的转写内容
    logger.info(
        "whisper-callback: stt_task_id=%s transcript_len=%d filtered=%s confidence=%s text_preview=%s",
        stt_task_id, len(text), filtered, task["confidence"], repr(text[:80]) if text else "(empty)",
    )

    task["status"] = "done"
    task["transcript"] = text if text else None
    task["error"] = None
    task["updated_at"] = utcnow()

    await broadcast(session_id, EVENT_STT_TASK_DONE, task)

    if text and not filtered:
        import uuid

        note_id = f"note_{uuid.uuid4().hex[:8]}"
        now = utcnow()
        ts = body.get("created_at") or now.isoformat()
        try:
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            ts_dt = now

        new_note = {
            "id": note_id,
            "session_id": session_id,
            "timestamp": ts_dt,
            "speaker": None,
            "content": text,
            "type": "observation",
            "tags": [],
            "telemetry_snapshot": None,
            "confidence": task.get("confidence"),
            "created_at": now,
            "updated_at": now,
        }
        notes_db[note_id] = new_note
        await broadcast(session_id, EVENT_NOTE_CREATED, new_note)

    return {"ok": True}
