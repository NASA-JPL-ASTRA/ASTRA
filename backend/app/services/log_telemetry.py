"""
Voice telemetry queries against InfluxDB telemetry.

Ported from realtime_demo.py for use by the ASTRA backend and frontend.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx

from app.services.influx_query import (
    count_channel_samples,
    get_channel_samples,
    get_session_events,
    query_channel_range_default,
)

logger = logging.getLogger(__name__)

UNKNOWN_QUERY_REPLY = (
    "Could not interpret this as a telemetry query. "
    "Ask about telemetry events (e.g., terrain bump) or channel signals "
    "(e.g., imu.accel_x, motors.motor1_current)."
)

DEFAULT_EVENT_MERGE_WINDOW_SEC = float(os.getenv("EVENT_MERGE_WINDOW_SEC", "0.05"))

# Map legacy / LLM scenario names to generator output folder names.
SCENARIO_FOLDER_ALIASES: dict[str, str] = {
    "test_2_nominal_mission": "test_2_uphill",
}


SCENARIO_ALIASES: dict[str, list[str]] = {
    "test_1_straight_line": ["straight line", "straight-line", "test 1", "test_1", "straight"],
    "test_2_uphill": ["test 2", "test_2", "uphill", "uphill climb", "nominal mission", "nominal trajectory"],
    "test_3_stops_starts_turns": ["test 3", "test_3", "stops starts turns", "stop start turn"],
    "test_4_motor_stall": ["test 4", "test_4", "motor stall", "stall"],
    "test_5_imu_malfunction": ["test 5", "test_5", "imu malfunction", "imu anomaly"],
    "test_6_command_error": ["test 6", "test_6", "command error"],
}

EVENT_FILTER_ALIASES: dict[str, list[str]] = {
    "bump": ["bump", "obstacle"],
    "nav.bump_detected": ["nav.bump_detected", "bump", "obstacle"],
    "stall": ["stall", "obstacle", "current_limit", "emergency_stop"],
    "motor stall": ["stall", "obstacle", "current_limit", "emergency_stop"],
    "current limit": ["current_limit", "current limit", "current exceeded"],
    "fault": ["fault", "current_limit", "anomaly", "rejected"],
    "imu": ["imu", "data_anomaly", "selftest"],
    "command error": ["command", "invalid_format", "rejected", "parser"],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_telemetry_log_root() -> Path:
    raw = os.getenv(
        "TELEMETRY_LOG_ROOT", "telemetry/telemetry-generator/output"
    ).strip()
    root = Path(raw)
    if not root.is_absolute():
        root = _repo_root() / root
    return root


def get_default_scenario() -> str:
    return os.getenv("TELEMETRY_DEFAULT_SCENARIO", "test_1_straight_line").strip()


def is_voice_telemetry_enabled() -> bool:
    flag = os.getenv("VOICE_TELEMETRY_ENABLED", "true").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def list_log_scenarios(telemetry_root: Path | None = None) -> list[str]:
    root = telemetry_root or get_telemetry_log_root()
    scenarios = set(SCENARIO_ALIASES.keys())
    if not root.is_dir():
        return sorted(scenarios)
    scenarios.update(
        p.name
        for p in root.iterdir()
        if p.is_dir()
        and (
            (p / "event.log").exists()
            or (p / "channel.log").exists()
        )
    )
    return sorted(scenarios)


def normalize_scenario_folder(name: str | None, default: str) -> str:
    """Resolve scenario string to an existing output/ subdirectory name."""
    if not name or not str(name).strip():
        return default
    folder = str(name).strip()
    return SCENARIO_FOLDER_ALIASES.get(folder, folder)


def infer_scenario_from_transcript(transcript: str, default_scenario: str) -> str:
    text = transcript.lower()
    for scenario, aliases in SCENARIO_ALIASES.items():
        if scenario.lower() in text:
            return scenario
        if any(alias in text for alias in aliases):
            return scenario
    return default_scenario


async def _openai_chat_json(
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float,
    system: str,
    user: str,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        body = response.json()
    content = ""
    choices = body.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content") or ""
    return json.loads(content)


async def parse_command_intent(
    *,
    transcript: str,
    default_scenario: str,
    api_key: str,
    base_url: str,
    intent_model: str,
    timeout: float,
) -> dict[str, Any]:
    schema_hint = {
        "action": "query_event_log | query_channel_log | query_channel_at_event | unknown",
        "scenario": "telemetry scenario folder name or null",
        "event_filter": "event type filter like nav.bump_detected or null",
        "field": "target field such as y or null",
        "signal_names": ["imu.accel_x", "motors.motor1_current"],
        "aggregation": "list | latest | min | max | avg | null",
        "time_tolerance_sec": "float seconds window for matching channel samples to event timestamp (e.g. 0.2) or null",
    }
    prompt = (
        "You are an intent parser for ASTRA rover voice commands.\n"
        "Return ONLY JSON, with no markdown.\n"
        f"JSON schema hint: {json.dumps(schema_hint)}\n\n"
        "Known scenario folders:\n"
        "- test_1_straight_line\n"
        "- test_2_uphill\n"
        "- test_3_stops_starts_turns\n"
        "- test_4_motor_stall\n"
        "- test_5_imu_malfunction\n"
        "- test_6_command_error\n\n"
        "Rules:\n"
        "- Valid query actions:\n"
        "  - query_event_log: query telemetry events from InfluxDB\n"
        "  - query_channel_log: query channel values from InfluxDB\n"
        "  - query_channel_at_event: find channel signal values at/near matching event timestamps\n"
        "- If user asks for telemetry events, set action=query_event_log.\n"
        "- If user asks for signals like imu.accel_x or motors.motor1_current, set action=query_channel_log.\n"
        "- If user asks 'value of <signal> when <event> happens' or 'at the time of <event>' then set action=query_channel_at_event.\n"
        "- For query_channel_at_event, you MUST set event_filter and signal_names.\n"
        "- Do NOT invent any other action type; if the utterance is not clearly a telemetry query, set action=unknown.\n"
        "- If scenario is not explicit, infer from wording if possible; otherwise keep null.\n"
        "- If asking for all matches, use aggregation=list.\n"
        "- If unknown, set action=unknown.\n\n"
        f"Transcript:\n{transcript}"
    )
    try:
        parsed = await _openai_chat_json(
            api_key=api_key,
            base_url=base_url,
            model=intent_model,
            timeout=timeout,
            system="You are strict about returning valid JSON only.",
            user=prompt,
        )
    except Exception:
        logger.exception("Intent parse failed")
        parsed = {"action": "unknown"}

    return {
        "action": parsed.get("action") or "unknown",
        "scenario": parsed.get("scenario") or default_scenario,
        "event_filter": parsed.get("event_filter"),
        "field": parsed.get("field"),
        "signal_names": parsed.get("signal_names") or [],
        "aggregation": parsed.get("aggregation") or "list",
        "time_tolerance_sec": parsed.get("time_tolerance_sec"),
    }


def _format_ts(ts: float) -> str:
    return f"{ts:.6f}".rstrip("0").rstrip(".")


def _event_filter_terms(filter_text: str) -> list[str]:
    if not filter_text:
        return []
    terms = {filter_text}
    terms.update(EVENT_FILTER_ALIASES.get(filter_text, []))
    for key, aliases in EVENT_FILTER_ALIASES.items():
        if key in filter_text:
            terms.update(aliases)
    terms.update(part for part in re.split(r"[._\s-]+", filter_text) if len(part) >= 4)
    return sorted(terms, key=len, reverse=True)


def _event_matches(event: dict[str, Any], filter_text: str) -> bool:
    terms = _event_filter_terms(filter_text)
    if not terms:
        return True
    evr_name = str(event.get("evr_name") or "").lower()
    message = str(event.get("message") or "").lower()
    return any(term in evr_name or term in message for term in terms)


def query_event_log(
    telemetry_root: Path,
    scenario: str,
    event_filter: str | None,
    field: str | None,
    aggregation: str,
) -> str:
    del telemetry_root
    wanted_field = (field or "").strip().lower()
    filter_text = (event_filter or "").strip().lower()
    y_pattern = re.compile(r"\by\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*m\b", re.IGNORECASE)

    matches: list[tuple[str, str, str]] = []
    for event in get_session_events(session_id=scenario):
        if not _event_matches(event, filter_text):
            continue
        matches.append(
            (
                _format_ts(float(event["timestamp"])),
                str(event.get("evr_name") or ""),
                str(event.get("message") or ""),
            )
        )

    if not matches:
        return f"No matching events found in Influx session '{scenario}'."

    if wanted_field == "y" or ("bump" in filter_text and not wanted_field):
        y_vals: list[float] = []
        for _ts, _etype, message in matches:
            m = y_pattern.search(message)
            if m:
                y_vals.append(float(m.group(1)))
        if not y_vals:
            if wanted_field == "y":
                return f"Found {len(matches)} events, but no 'y=...m' values were extracted."
        else:
            unique_y = sorted(set(y_vals))
            if aggregation == "latest":
                return f"Latest y position for terrain bump in {scenario}: y={unique_y[-1]:.1f}m"
            return "Terrain bump y positions: " + ", ".join(f"y={v:.1f}m" for v in unique_y)

    if aggregation == "latest":
        ts, etype, msg = matches[-1]
        return f"Latest event in {scenario}: [{ts}] {etype} - {msg}"

    def merge_near_duplicates(
        items: list[tuple[str, str, str]],
        window_sec: float,
    ) -> list[tuple[str, str, str, int]]:
        if not items:
            return []
        merged: list[tuple[str, str, str, int]] = []
        cur_ts, cur_etype, cur_msg = items[0]
        cur_count = 1
        try:
            cur_ts_f = float(cur_ts)
        except ValueError:
            cur_ts_f = None

        for ts, etype, msg in items[1:]:
            same_payload = etype == cur_etype and msg == cur_msg
            try:
                ts_f = float(ts)
            except ValueError:
                ts_f = None

            within = False
            if cur_ts_f is not None and ts_f is not None:
                within = (ts_f - cur_ts_f) <= window_sec

            if same_payload and within:
                cur_count += 1
                continue

            merged.append((cur_ts, cur_etype, cur_msg, cur_count))
            cur_ts, cur_etype, cur_msg = ts, etype, msg
            cur_count = 1
            cur_ts_f = ts_f

        merged.append((cur_ts, cur_etype, cur_msg, cur_count))
        return merged

    lines = [f"Found {len(matches)} matching events in {scenario}:"]
    merged = merge_near_duplicates(matches, window_sec=DEFAULT_EVENT_MERGE_WINDOW_SEC)
    if len(merged) != len(matches):
        lines[0] = (
            f"Found {len(matches)} matching events in {scenario} "
            f"(merged to {len(merged)} within {DEFAULT_EVENT_MERGE_WINDOW_SEC:.3f}s):"
        )
    for ts, etype, msg, count in merged:
        suffix = f" (x{count})" if count > 1 else ""
        lines.append(f"- [{ts}] {etype}: {msg}{suffix}")
    return "\n".join(lines)


def query_channel_log(
    telemetry_root: Path,
    scenario: str,
    signal_names: list[str],
    aggregation: str,
) -> str:
    del telemetry_root
    wanted = [s.strip() for s in signal_names if s and s.strip()]
    if not wanted:
        return "No signal names provided for channel query (e.g., imu.accel_x, motors.motor1_current)."

    lines = [f"Influx channel query results for {scenario}:"]
    for signal in wanted:
        stats = query_channel_range_default(session_id=scenario, channel=signal)
        if not stats:
            lines.append(f"- {signal}: not found")
            continue
        if aggregation == "latest":
            lines.append(f"- {signal}: latest={float(stats['last']):.4f}")
        elif aggregation == "min":
            lines.append(f"- {signal}: min={float(stats['min']):.4f}")
        elif aggregation == "max":
            lines.append(f"- {signal}: max={float(stats['max']):.4f}")
        elif aggregation == "avg":
            lines.append(f"- {signal}: avg={float(stats['mean']):.4f}")
        else:
            samples = get_channel_samples(session_id=scenario, channel=signal, limit=10)
            total = count_channel_samples(session_id=scenario, channel=signal)
            preview = ", ".join(f"{float(item['value']):.4f}" for item in samples)
            suffix = " ..." if total > len(samples) else ""
            lines.append(f"- {signal}: [{preview}{suffix}] (count={total})")
    return "\n".join(lines)


def _nearest_sample(samples: list[dict[str, Any]], target_ts: float) -> dict[str, Any] | None:
    if not samples:
        return None
    return min(samples, key=lambda item: abs(float(item["timestamp"]) - target_ts))


def _merge_near_duplicate_events(
    events: list[tuple[str, float, str, str]],
    window_sec: float,
) -> list[tuple[str, float, str, str]]:
    if not events:
        return []
    merged = [events[0]]
    for event in events[1:]:
        _last_raw, last_ts, last_type, last_msg = merged[-1]
        _raw, ts, event_type, msg = event
        if event_type == last_type and msg == last_msg and (ts - last_ts) <= window_sec:
            continue
        merged.append(event)
    return merged


def query_channel_at_event(
    telemetry_root: Path,
    scenario: str,
    event_filter: str | None,
    signal_names: list[str],
    time_tolerance_sec: float = 0.2,
    aggregation: str = "list",
) -> str:
    del telemetry_root
    filter_text = (event_filter or "").strip().lower()
    if not filter_text:
        return "No event filter provided for event/channel join query."

    wanted = [s.strip() for s in (signal_names or []) if s and s.strip()]
    if not wanted:
        return "No signal names provided for event/channel join query."

    event_ts: list[tuple[str, float, str, str]] = []
    for event in get_session_events(session_id=scenario):
        if not _event_matches(event, filter_text):
            continue
        ts = float(event["timestamp"])
        event_ts.append(
            (
                _format_ts(ts),
                ts,
                str(event.get("evr_name") or ""),
                str(event.get("message") or ""),
            )
        )

    if not event_ts:
        return f"No matching events found in Influx session '{scenario}' for filter '{event_filter}'."

    if aggregation == "latest":
        event_ts = [event_ts[-1]]
    else:
        event_ts = _merge_near_duplicate_events(
            event_ts,
            window_sec=DEFAULT_EVENT_MERGE_WINDOW_SEC,
        )

    lines: list[str] = [
        f"Influx event/channel join results for {scenario} "
        f"(event filter='{event_filter}', tolerance={time_tolerance_sec:.3f}s):"
    ]
    for i, (event_ts_raw, ets, etype, msg) in enumerate(event_ts, start=1):
        lines.append(f"{i}. Event @ {event_ts_raw} [{etype}]: {msg}")
        for sig in wanted:
            samples = get_channel_samples(
                session_id=scenario,
                channel=sig,
                start_time=ets - time_tolerance_sec,
                end_time=ets + time_tolerance_sec,
                limit=200,
            )
            nearest = _nearest_sample(samples, ets)
            if not nearest:
                lines.append(f"   - {sig}: not found")
                continue
            sts = float(nearest["timestamp"])
            val = float(nearest["value"])
            dt = abs(sts - ets)
            lines.append(
                f"   - {sig}: {val:.4f} (sample @ {_format_ts(sts)}, dt={dt:.3f}s)"
            )

    return "\n".join(lines)


def execute_intent(
    intent: dict[str, Any],
    *,
    telemetry_root: Path,
    default_scenario: str,
) -> str:
    scenario = normalize_scenario_folder(intent.get("scenario"), default_scenario)
    action = intent.get("action", "unknown")
    aggregation = intent.get("aggregation", "list")

    if action == "query_event_log":
        return query_event_log(
            telemetry_root=telemetry_root,
            scenario=scenario,
            event_filter=intent.get("event_filter"),
            field=intent.get("field"),
            aggregation=aggregation,
        )
    if action == "query_channel_log":
        return query_channel_log(
            telemetry_root=telemetry_root,
            scenario=scenario,
            signal_names=intent.get("signal_names") or [],
            aggregation=aggregation,
        )
    if action == "query_channel_at_event":
        tol_raw = intent.get("time_tolerance_sec")
        try:
            tol = float(tol_raw) if tol_raw is not None else 0.2
        except (TypeError, ValueError):
            tol = 0.2
        tol = max(0.2, tol)
        return query_channel_at_event(
            telemetry_root=telemetry_root,
            scenario=scenario,
            event_filter=intent.get("event_filter"),
            signal_names=intent.get("signal_names") or [],
            time_tolerance_sec=tol,
            aggregation=aggregation,
        )
    return UNKNOWN_QUERY_REPLY


async def answer_from_transcript(
    transcript: str,
    *,
    telemetry_root: Path | None = None,
    default_scenario: str | None = None,
) -> dict[str, Any]:
    """Parse intent and run log query; returns structured result for API/WS."""
    root = telemetry_root or get_telemetry_log_root()
    scenario_default = default_scenario or get_default_scenario()
    cleaned = transcript.strip()
    if not cleaned:
        return {
            "transcript": transcript,
            "action": "unknown",
            "scenario": scenario_default,
            "intent": {},
            "answer": UNKNOWN_QUERY_REPLY,
            "is_telemetry_query": False,
        }

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").strip()
    intent_model = os.getenv("OPENAI_INTENT_MODEL", os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o-mini"))
    timeout = float(os.getenv("OPENAI_STT_TIMEOUT_SECONDS", "120"))

    inferred = infer_scenario_from_transcript(cleaned, scenario_default)
    intent = await parse_command_intent(
        transcript=cleaned,
        default_scenario=inferred,
        api_key=api_key,
        base_url=base_url,
        intent_model=intent_model,
        timeout=timeout,
    )
    answer = execute_intent(intent, telemetry_root=root, default_scenario=inferred)
    action = intent.get("action", "unknown")
    is_query = action != "unknown" and answer.strip() != UNKNOWN_QUERY_REPLY.strip()

    scenario = normalize_scenario_folder(intent.get("scenario"), inferred)
    return {
        "transcript": cleaned,
        "action": action,
        "scenario": scenario,
        "intent": intent,
        "answer": answer,
        "is_telemetry_query": is_query,
    }
