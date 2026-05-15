"""
Natural-language telemetry query planner.

The LLM is only allowed to choose a small set of safe query actions; execution
stays in the existing Influx helper functions instead of running arbitrary Flux.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import httpx

from app.services.channel_search import CHANNEL_DICTIONARY, search_channel
from app.services.influx_query import (
    get_channel_value,
    get_recent_events,
    query_channel_range,
)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_TELEMETRY_MODEL = os.getenv(
    "OPENAI_TELEMETRY_QUERY_MODEL",
    os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5-mini"),
)

VALID_ACTIONS = {"channel_value", "channel_range", "events", "search"}
VALID_SEVERITIES = {"all", "warning", "activity_hi", "activity_lo", "command"}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


async def _call_openai(instructions: str, input_text: str, model: str | None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    payload = {
        "model": model or DEFAULT_TELEMETRY_MODEL,
        "instructions": instructions,
        "input": input_text,
    }

    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                texts.append(content["text"])
    if texts:
        return "\n".join(texts).strip()

    raise RuntimeError("OpenAI response did not include text output")


def _num(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _default_window(t0: float | None, t1: float | None, at: float | None) -> tuple[float, float, float]:
    now = time.time()
    end = t1 if t1 is not None else at if at is not None else now
    start = t0 if t0 is not None else end - 400
    if start >= end:
        start = end - 400
    return start, end, at if at is not None else end


def _normalize_plan(
    raw: dict[str, Any],
    *,
    question: str,
    session: str | None,
    t0: float | None,
    t1: float | None,
    at: float | None,
    severity: str,
    limit: int,
) -> dict[str, Any]:
    start, end, point_at = _default_window(t0, t1, at)
    action = str(raw.get("action") or "").strip()
    if action not in VALID_ACTIONS:
        action = "channel_range"

    channel = str(raw.get("channel") or "").strip()
    if channel not in CHANNEL_DICTIONARY:
        candidates = search_channel(channel or question, top_k=1)
        channel = candidates[0]["channel"] if candidates else ""

    sev = str(raw.get("severity") or severity or "all").strip()
    if sev not in VALID_SEVERITIES:
        sev = "all"

    lim = int(_num(raw.get("limit"), limit))
    lim = max(1, min(500, lim))

    return {
        "action": action,
        "session": str(raw.get("session") or session or "").strip(),
        "channel": channel,
        "at": _num(raw.get("at"), point_at),
        "t0": _num(raw.get("t0"), start),
        "t1": _num(raw.get("t1"), end),
        "severity": sev,
        "limit": lim,
        "reason": str(raw.get("reason") or "").strip(),
        "query": question,
    }


def _fallback_plan(
    *,
    question: str,
    session: str | None,
    t0: float | None,
    t1: float | None,
    at: float | None,
    severity: str,
    limit: int,
) -> dict[str, Any]:
    q = question.lower()
    start, end, point_at = _default_window(t0, t1, at)
    if any(term in q for term in ("event", "warning", "fault", "alarm", "異常", "告警", "故障")):
        action = "events"
        channel = ""
    else:
        candidates = search_channel(question, top_k=1)
        channel = candidates[0]["channel"] if candidates else ""
        action = "channel_value" if any(term in q for term in ("latest", "current", "now", "目前", "現在")) else "channel_range"
        if not channel:
            action = "search"

    return {
        "action": action,
        "session": session or "",
        "channel": channel,
        "at": point_at,
        "t0": start,
        "t1": end,
        "severity": severity if severity in VALID_SEVERITIES else "all",
        "limit": max(1, min(500, limit)),
        "reason": "Local fallback plan; LLM planner was unavailable.",
        "query": question,
    }


async def plan_telemetry_query(
    *,
    question: str,
    session: str | None,
    t0: float | None,
    t1: float | None,
    at: float | None,
    severity: str,
    limit: int,
    model: str | None,
) -> dict[str, Any]:
    start, end, point_at = _default_window(t0, t1, at)
    candidates = search_channel(question, top_k=5)
    instructions = (
        "You plan safe InfluxDB telemetry lookups for ASTRA. Return ONLY JSON. "
        "Choose one action from: channel_value, channel_range, events, search. "
        "Use channel_value for latest/current value at a point in time. "
        "Use channel_range for min/max/mean/last over a window. "
        "Use events for warnings, faults, commands, anomalies, or EVR messages. "
        "Use search only when the user is asking which channel matches a concept. "
        "Pick channel only from known_channels. Keep timestamps as Unix seconds."
    )
    input_text = json.dumps(
        {
            "question": question,
            "default_session": session,
            "default_t0": start,
            "default_t1": end,
            "default_at": point_at,
            "default_severity": severity,
            "default_limit": limit,
            "search_candidates": candidates,
            "known_channels": list(CHANNEL_DICTIONARY.keys()),
            "response_schema": {
                "action": "channel_value|channel_range|events|search",
                "session": "string",
                "channel": "string or empty",
                "at": "number",
                "t0": "number",
                "t1": "number",
                "severity": "all|warning|activity_hi|activity_lo|command",
                "limit": "integer",
                "reason": "short string",
            },
        },
        ensure_ascii=False,
    )

    try:
        raw = await _call_openai(instructions, input_text, model)
        parsed = _extract_json_object(raw) or {}
        return _normalize_plan(
            parsed,
            question=question,
            session=session,
            t0=t0,
            t1=t1,
            at=at,
            severity=severity,
            limit=limit,
        )
    except Exception as exc:
        plan = _fallback_plan(
            question=question,
            session=session,
            t0=t0,
            t1=t1,
            at=at,
            severity=severity,
            limit=limit,
        )
        plan["planner_error"] = str(exc)
        return plan


def execute_telemetry_plan(plan: dict[str, Any]) -> tuple[Any, str | None]:
    action = plan.get("action")
    session = str(plan.get("session") or "").strip()

    if action == "search":
        return search_channel(str(plan.get("query") or plan.get("channel") or ""), top_k=plan.get("limit", 5)), None

    if not session:
        return None, "Missing Influx session tag."

    if action == "events":
        return get_recent_events(
            session_id=session,
            start_time=float(plan["t0"]),
            end_time=float(plan["t1"]),
            severity=str(plan.get("severity") or "all"),
            limit=int(plan.get("limit") or 20),
        ), None

    channel = str(plan.get("channel") or "").strip()
    if not channel:
        return None, "Could not identify a telemetry channel."

    if action == "channel_value":
        data = get_channel_value(session_id=session, channel=channel, at_time=float(plan["at"]))
        return data, None if data is not None else f"No value found for {channel}."

    data = query_channel_range(
        session_id=session,
        channel=channel,
        start_time=float(plan["t0"]),
        end_time=float(plan["t1"]),
    )
    return data, None if data is not None else f"No range data found for {channel}."


def summarize_telemetry_result(plan: dict[str, Any], data: Any, error: str | None) -> str:
    if error:
        return error

    action = plan.get("action")
    channel = plan.get("channel")
    if action == "channel_value" and isinstance(data, dict):
        return f"{channel} was {data.get('value')} at {data.get('timestamp')}."
    if action == "channel_range" and isinstance(data, dict):
        return (
            f"{channel}: min {data.get('min')}, max {data.get('max')}, "
            f"mean {data.get('mean')}, last {data.get('last')}."
        )
    if action == "events" and isinstance(data, list):
        return f"Found {len(data)} telemetry event(s) in the selected window."
    if action == "search" and isinstance(data, list):
        channels = ", ".join(str(item.get("channel")) for item in data[:5])
        return f"Matching channels: {channels or 'none'}."
    return "Telemetry query completed."
