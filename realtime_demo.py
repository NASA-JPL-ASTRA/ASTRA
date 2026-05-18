#!/usr/bin/env python3
"""
JPL ASTRA - Real-time STT Quick Demo
====================================
Quasi-real-time speech-to-text using VAD (pause-based segmentation) + OpenAI APIs.

Flow:
  1. Microphone records continuously
  2. VAD detects speech pause (configurable, default ~1.5s silence = end of utterance)
  3. Audio chunk saved as WAV
  4. Send WAV to OpenAI gpt-4o-transcribe -> get transcript
  5. Intent routing: query_event_log or query_channel_log only (no per-utterance engineering summary)
  6. Append transcript + query answer to engineering log file
  7. After the operator ends a voice session (e.g. via frontend), run with --finalize-session
     to roll up that day's successful query records into one session engineering log entry
  8. Loop

Requirements:
  python -m pip install -r requirements.txt

Usage:
  python realtime_demo.py [--openai-api-key KEY] [--silence-sec 1.5] [--min-speech-sec 0.45]
  python realtime_demo.py --openai-api-key sk-... --log-path engineering_log.md

If --openai-api-key is omitted, OPENAI_API_KEY from environment is used.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI

# Load .env before reading defaults from environment variables.
load_dotenv()

# OpenAI models
DEFAULT_ASR_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-transcribe")
DEFAULT_SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5.5")
DEFAULT_INTENT_MODEL = os.getenv("OPENAI_INTENT_MODEL", "gpt-5.5")
DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "").strip() or None
DEFAULT_STT_LANGUAGE = os.getenv("OPENAI_STT_LANGUAGE", "").strip() or None
DEFAULT_STT_PROMPT = os.getenv("OPENAI_STT_PROMPT", "").strip() or None
DEFAULT_OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_STT_TIMEOUT_SECONDS", "120"))
DEFAULT_LOG_PATH = "engineering_log.md"
DEFAULT_TELEMETRY_ROOT = "telemetry/telemetry-generator/output"
DEFAULT_SCENARIO = "test_1_straight_line"

# Shown when intent is not a telemetry query; also used to exclude non-queries from session roll-up.
UNKNOWN_QUERY_REPLY = (
    "Could not interpret this as a telemetry query. "
    "Ask about events in event.log (e.g., terrain bump) or signals in channel.log "
    "(e.g., imu.accel_x, motors.motor1_current)."
)

SESSION_ROLLUP_HEADING = "### Session roll-up (operator work summary)"

# When event.log contains near-duplicate records (e.g., same message repeated within ~10ms),
# merge them into a single line for readability.
DEFAULT_EVENT_MERGE_WINDOW_SEC = float(os.getenv("EVENT_MERGE_WINDOW_SEC", "0.05"))

SCENARIO_FOLDER_ALIASES = {
    "test_2_nominal_mission": "test_2_uphill",
}

SCENARIO_ALIASES = {
    "test_1_straight_line": ["straight line", "straight-line", "test 1", "test_1", "straight"],
    "test_2_uphill": ["test 2", "test_2", "uphill", "uphill climb", "nominal mission", "nominal trajectory"],
    "test_3_stops_starts_turns": ["test 3", "test_3", "stops starts turns", "stop start turn"],
    "test_4_motor_stall": ["test 4", "test_4", "motor stall", "stall"],
    "test_5_imu_malfunction": ["test 5", "test_5", "imu malfunction", "imu anomaly"],
    "test_6_command_error": ["test 6", "test_6", "command error"],
}

# Audio config (Silero VAD runs at 16k for this demo)
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
SILERO_WINDOW_MS = 480
SILERO_TAIL_MS = 120
SILERO_THRESHOLD = 0.5

# Timing: NOT from Backend README (it says "configurable threshold" but no values).
# Chosen as reasonable defaults - you can tune via --silence-sec and --min-speech-sec:
# - 1.5s silence: common in voice assistants; shorter = more chunks, longer = wait more
# - 0.45s min: avoid noise bursts; shorter = more false triggers, longer = miss quick words
DEFAULT_SILENCE_SEC = 1.5
DEFAULT_MIN_SPEECH_SEC = 0.45

# Use shared hallucination filter (same logic as task_processor for consistency)
try:
    from app.utils.hallucination_filter import is_likely_hallucination
except ImportError:
    # Fallback when run outside project
    def is_likely_hallucination(transcript: str, segments: list, debug: bool = False) -> bool:
        for seg in segments or []:
            if seg.get("no_speech_prob", 0) > 0.4 or (seg.get("avg_logprob") or 0) < -0.5:
                return True
        t = transcript.strip().lower().rstrip(".,!? ")
        return len(t) <= 25 and t in {"thank you", "thanks", "okay", "ok", "bye", "you", "the", "end", "um", "uh"}


def transcribe_with_openai(
    client: OpenAI,
    wav_path: Path,
    asr_model: str,
    stt_language: str | None = None,
    stt_prompt: str | None = None,
) -> str:
    """Transcribe local WAV file with OpenAI audio transcription API."""
    with open(wav_path, "rb") as audio_file:
        request_data = {
            "model": asr_model,
            "file": audio_file,
            "response_format": "text",
        }
        if stt_language:
            request_data["language"] = stt_language
        if stt_prompt:
            request_data["prompt"] = stt_prompt
        transcript = client.audio.transcriptions.create(**request_data)
    return transcript.strip()


def summarize_query_session_for_engineering_log(
    client: OpenAI,
    query_records: list[tuple[str, str]],
    summary_model: str,
) -> str:
    """
    One engineering-log narrative from many (transcript, query_answer) pairs.
    Intended when the operator ends a voice session after running telemetry queries.
    """
    if not query_records:
        return ""
    lines = []
    for i, (tr, ans) in enumerate(query_records, start=1):
        lines.append(f"--- Query {i} ---\nVoice / intent (transcript): {tr}\nASTRA result:\n{ans}\n")
    bundle = "\n".join(lines)
    response = client.chat.completions.create(
        model=summary_model,
        messages=[
            {
                "role": "system",
                "content": "You are a senior technical project assistant who writes clear engineering logs.",
            },
            {
                "role": "user",
                "content": (
                    "Below is a chronological list of voice commands from one operator session and the "
                    "corresponding telemetry query results (event.log / channel.log only).\n"
                    "Write ONE engineering log entry for what this operator did in this session, with exactly "
                    "three sections:\n"
                    "1) Progress Today (what they investigated and found)\n"
                    "2) Issues and Risks (anomalies, gaps, or uncertainties in the data or questions)\n"
                    "3) Next Actions (concrete follow-ups)\n\n"
                    "Requirements: concise, actionable, preserve important technical terms and numbers from the results.\n\n"
                    f"Session query log:\n{bundle}"
                ),
            },
        ],
    )
    content = response.choices[0].message.content if response.choices else ""
    return (content or "").strip()


def format_rollup_summary_numbered(summary: str) -> str:
    """
    Convert top-level bullet points ('- ' or '* ') into numbered points within each section.
    Resets numbering on blank lines or heading-like lines.
    """
    if not summary.strip():
        return summary

    out_lines: list[str] = []
    n = 0

    def is_heading(line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        if s.startswith("#"):
            return True
        if re.match(r"^\d+\)", s) or re.match(r"^\d+\.", s):
            return True
        # Common section headings from the prompt
        if s.lower().startswith(("progress today", "issues and risks", "next actions")):
            return True
        return False

    for line in summary.splitlines():
        if not line.strip():
            n = 0
            out_lines.append(line)
            continue
        if is_heading(line):
            n = 0
            out_lines.append(line)
            continue

        m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if m:
            indent, rest = m.group(1), m.group(2)
            n += 1
            out_lines.append(f"{indent}{n}. {rest}")
        else:
            out_lines.append(line)

    return "\n".join(out_lines).strip()


def parse_command_intent(
    client: OpenAI,
    transcript: str,
    intent_model: str,
    default_scenario: str,
) -> dict:
    """
    Parse transcript into structured command intent using an LLM.
    Returns a dict with keys:
      action, scenario, event_filter, field, signal_names, aggregation, time_tolerance_sec
    """
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
        "  - query_event_log: read event.log\n"
        "  - query_channel_log: read channel.log\n"
        "  - query_channel_at_event: find channel signal values at/near the timestamps of matching events\n"
        "- If user asks for events from event.log, set action=query_event_log.\n"
        "- If user asks for signals like imu.accel_x or motors.motor1_current from channel.log, set action=query_channel_log.\n"
        "- If user asks 'value of <signal> when <event> happens' or 'at the time of <event>' then set action=query_channel_at_event.\n"
        "- For query_channel_at_event, you MUST set event_filter and signal_names.\n"
        "- Do NOT invent any other action type; if the utterance is not clearly a telemetry query, set action=unknown.\n"
        "- If scenario is not explicit, infer from wording if possible; otherwise keep null.\n"
        "- If asking for all matches, use aggregation=list.\n"
        "- If unknown, set action=unknown.\n\n"
        f"Transcript:\n{transcript}"
    )

    try:
        response = client.chat.completions.create(
            model=intent_model,
            messages=[
                {"role": "system", "content": "You are strict about returning valid JSON only."},
                {"role": "user", "content": prompt},
            ],
        )
        content = (response.choices[0].message.content if response.choices else "") or ""
        parsed = json.loads(content)
    except Exception:
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


def normalize_scenario_folder(name: str | None, default: str) -> str:
    if not name or not str(name).strip():
        return default
    folder = str(name).strip()
    return SCENARIO_FOLDER_ALIASES.get(folder, folder)


def infer_scenario_from_transcript(transcript: str, default_scenario: str) -> str:
    """Infer telemetry scenario from transcript keywords."""
    text = transcript.lower()
    for scenario, aliases in SCENARIO_ALIASES.items():
        if scenario.lower() in text:
            return scenario
        if any(alias in text for alias in aliases):
            return scenario
    return default_scenario


def query_event_log(
    telemetry_root: Path,
    scenario: str,
    event_filter: str | None,
    field: str | None,
    aggregation: str,
) -> str:
    """Query event.log for target events/fields and return human-readable answer."""
    event_path = telemetry_root / scenario / "event.log"
    if not event_path.exists():
        return f"event.log not found for scenario '{scenario}' at: {event_path}"

    wanted_field = (field or "").strip().lower()
    filter_text = (event_filter or "").strip().lower()
    y_pattern = re.compile(r"\by\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*m\b", re.IGNORECASE)

    matches = []
    with event_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            ts, event_type, _severity, message = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            event_type_lower = event_type.lower()
            message_lower = message.lower()
            if filter_text and (filter_text not in event_type_lower and filter_text not in message_lower):
                continue
            matches.append((ts, event_type, message))

    if not matches:
        return f"No matching events found in '{scenario}/event.log'."

    # Specialized extraction for y from terrain bump events
    if wanted_field == "y" or ("bump" in filter_text and not wanted_field):
        y_vals = []
        for _ts, _etype, message in matches:
            m = y_pattern.search(message)
            if m:
                y_vals.append(float(m.group(1)))
        if not y_vals:
            return f"Found {len(matches)} events, but no 'y=...m' values were extracted."
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
        """
        Merge consecutive identical (etype,msg) items whose timestamps are within window_sec.
        Returns list of (ts, etype, msg, count_merged).
        """
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
            same_payload = (etype == cur_etype and msg == cur_msg)
            try:
                ts_f = float(ts)
            except ValueError:
                ts_f = None

            within = False
            if cur_ts_f is not None and ts_f is not None:
                within = (ts_f - cur_ts_f) <= window_sec

            if same_payload and within:
                cur_count += 1
                # keep earliest timestamp as representative
                continue

            merged.append((cur_ts, cur_etype, cur_msg, cur_count))
            cur_ts, cur_etype, cur_msg = ts, etype, msg
            cur_count = 1
            cur_ts_f = ts_f

        merged.append((cur_ts, cur_etype, cur_msg, cur_count))
        return merged

    lines = [f"Found {len(matches)} matching events in {scenario}:"]
    merged = merge_near_duplicates(matches, window_sec=DEFAULT_EVENT_MERGE_WINDOW_SEC)
    # If merge reduced the list, reflect it in the header for clarity.
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
    """Query channel.log for signal values and return formatted answer."""
    channel_path = telemetry_root / scenario / "channel.log"
    if not channel_path.exists():
        return f"channel.log not found for scenario '{scenario}' at: {channel_path}"

    wanted = [s.strip() for s in signal_names if s and s.strip()]
    if not wanted:
        return "No signal names provided for channel.log query (e.g., imu.accel_x, motors.motor1_current)."

    values: dict[str, list[tuple[float, float]]] = {name: [] for name in wanted}
    with channel_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            ts_raw, signal, val_raw = row[0].strip(), row[1].strip(), row[2].strip()
            if signal not in values:
                continue
            try:
                ts = float(ts_raw)
                val = float(val_raw)
            except ValueError:
                continue
            values[signal].append((ts, val))

    lines = [f"channel.log query results for {scenario}:"]
    for signal in wanted:
        series = values.get(signal, [])
        if not series:
            lines.append(f"- {signal}: not found")
            continue
        nums = [v for _t, v in series]
        if aggregation == "latest":
            lines.append(f"- {signal}: latest={nums[-1]:.4f}")
        elif aggregation == "min":
            lines.append(f"- {signal}: min={min(nums):.4f}")
        elif aggregation == "max":
            lines.append(f"- {signal}: max={max(nums):.4f}")
        elif aggregation == "avg":
            lines.append(f"- {signal}: avg={sum(nums) / len(nums):.4f}")
        else:
            preview = ", ".join(f"{v:.4f}" for v in nums[:10])
            suffix = " ..." if len(nums) > 10 else ""
            lines.append(f"- {signal}: [{preview}{suffix}] (count={len(nums)})")
    return "\n".join(lines)


def _nearest_sample(
    series: list[tuple[float, float, str]], target_ts: float
) -> tuple[float, float, str] | None:
    """Return (ts, val, ts_raw) with minimal |ts-target_ts|. Series sorted by ts; ts_raw is CSV text."""
    if not series:
        return None
    lo, hi = 0, len(series) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if series[mid][0] < target_ts:
            lo = mid + 1
        else:
            hi = mid
    candidates = [series[lo]]
    if lo > 0:
        candidates.append(series[lo - 1])
    return min(candidates, key=lambda tv: abs(tv[0] - target_ts))


def query_channel_at_event(
    telemetry_root: Path,
    scenario: str,
    event_filter: str | None,
    signal_names: list[str],
    time_tolerance_sec: float = 0.2,
    aggregation: str = "list",
) -> str:
    """
    Match events from event.log and query channel.log values at/near each event timestamp.
    Uses nearest neighbor within time_tolerance_sec.
    """
    event_path = telemetry_root / scenario / "event.log"
    channel_path = telemetry_root / scenario / "channel.log"
    if not event_path.exists():
        return f"event.log not found for scenario '{scenario}' at: {event_path}"
    if not channel_path.exists():
        return f"channel.log not found for scenario '{scenario}' at: {channel_path}"

    filter_text = (event_filter or "").strip().lower()
    if not filter_text:
        return "No event filter provided for event/channel join query."

    wanted = [s.strip() for s in (signal_names or []) if s and s.strip()]
    if not wanted:
        return "No signal names provided for event/channel join query."

    # 1) Collect matching events: keep original timestamp string from CSV for display; float for matching.
    event_ts: list[tuple[str, float, str, str]] = []
    with event_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            ts_raw, event_type, _severity, message = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()
            et_l = event_type.lower()
            msg_l = message.lower()
            if filter_text and (filter_text not in et_l and filter_text not in msg_l):
                continue
            try:
                ts = float(ts_raw)
            except ValueError:
                continue
            event_ts.append((ts_raw, ts, event_type, message))

    if not event_ts:
        return f"No matching events found in '{scenario}/event.log' for filter '{event_filter}'."

    # For "latest" aggregation, only keep the last event.
    if aggregation == "latest":
        event_ts = [event_ts[-1]]

    # 2) Read channel samples for requested signals (keep ts_raw for display)
    series_by_signal: dict[str, list[tuple[float, float, str]]] = {name: [] for name in wanted}
    with channel_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            ts_raw, signal, val_raw = row[0].strip(), row[1].strip(), row[2].strip()
            if signal not in series_by_signal:
                continue
            try:
                ts = float(ts_raw)
                val = float(val_raw)
            except ValueError:
                continue
            series_by_signal[signal].append((ts, val, ts_raw))

    for sig in wanted:
        series_by_signal[sig].sort(key=lambda tv: tv[0])

    # 3) Join by nearest timestamp within tolerance
    lines: list[str] = []
    lines.append(
        f"event/channel join results for {scenario} (event filter='{event_filter}', tolerance={time_tolerance_sec:.3f}s):"
    )
    for i, (event_ts_raw, ets, etype, msg) in enumerate(event_ts, start=1):
        lines.append(f"{i}. Event @ {event_ts_raw} [{etype}]: {msg}")
        for sig in wanted:
            series = series_by_signal.get(sig) or []
            nearest = _nearest_sample(series, ets)
            if not nearest:
                lines.append(f"   - {sig}: not found")
                continue
            sts, val, sample_ts_raw = nearest
            dt = abs(sts - ets)
            if dt > time_tolerance_sec:
                lines.append(
                    f"   - {sig}: no sample within tolerance (nearest at {sample_ts_raw}, dt={dt:.3f}s)"
                )
            else:
                lines.append(
                    f"   - {sig}: {val:.4f} (sample @ {sample_ts_raw}, dt={dt:.3f}s)"
                )

    return "\n".join(lines)


def answer_from_transcript(
    client: OpenAI,
    transcript: str,
    intent_model: str,
    telemetry_root: Path,
    default_scenario: str,
) -> str:
    """Generate assistant answer by routing transcript to query_event_log or query_channel_log only."""
    inferred_scenario = infer_scenario_from_transcript(transcript, default_scenario)
    intent = parse_command_intent(
        client=client,
        transcript=transcript,
        intent_model=intent_model,
        default_scenario=inferred_scenario,
    )
    scenario = normalize_scenario_folder(intent.get("scenario"), inferred_scenario)
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
        return query_channel_at_event(
            telemetry_root=telemetry_root,
            scenario=scenario,
            event_filter=intent.get("event_filter"),
            signal_names=intent.get("signal_names") or [],
            time_tolerance_sec=tol,
            aggregation=aggregation,
        )
    return UNKNOWN_QUERY_REPLY


def append_engineering_log(log_path: Path, transcript: str, summary: str) -> None:
    """Append one timestamped transcript+summary block into engineering log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n## {ts}\n\n"
        f"### Transcript\n{transcript}\n\n"
        f"### Engineering Log Summary\n{summary}\n"
    )
    if not log_path.exists():
        log_path.write_text("# ASTRA Engineering Log\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(block)


def _parse_engineering_log_blocks(text: str) -> list[tuple[datetime, str, str]]:
    """
    Parse standard voice-query blocks (## timestamp + Transcript + Engineering Log Summary).
    Ignores session roll-up blocks and any malformed sections.
    """
    if not text.strip():
        return []
    # Split on "## " at line starts; first chunk may be preamble before first "##"
    parts = re.split(r"(?m)^## ", text)
    out: list[tuple[datetime, str, str]] = []
    for raw in parts:
        chunk = raw.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        if not lines:
            continue
        header = lines[0].strip()
        body = "\n".join(lines[1:]).lstrip("\n")
        try:
            ts = datetime.strptime(header, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        m_tr = re.search(r"(?ms)^### Transcript\s*\n(.*?)(?=^### Engineering Log Summary\s*$)", body)
        m_ans = re.search(r"(?ms)^### Engineering Log Summary\s*\n(.*)\Z", body)
        if not m_tr or not m_ans:
            continue
        transcript = m_tr.group(1).strip()
        answer = m_ans.group(1).strip()
        out.append((ts, transcript, answer))
    return out


def append_session_roll_up(log_path: Path, summary: str) -> None:
    """Append a single session-level engineering summary (no per-utterance transcript)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = (
        f"\n## {ts}\n\n"
        f"{SESSION_ROLLUP_HEADING}\n\n"
        f"{summary}\n"
    )
    if not log_path.exists():
        log_path.write_text("# ASTRA Engineering Log\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(block)


def run_finalize_session(
    openai_api_key: str,
    openai_api_base_url: str | None,
    openai_timeout_sec: float,
    summary_model: str,
    log_path: Path,
    session_date: datetime | None = None,
) -> None:
    """
    After queries for the day (or when the operator ends a voice session in the future UI),
    summarize all successful telemetry query entries from the log for that calendar day.
    """
    session_date = session_date or datetime.now()
    day = session_date.date()
    if not log_path.exists():
        print(f"No log file at {log_path}; nothing to finalize.")
        return
    text = log_path.read_text(encoding="utf-8")
    blocks = _parse_engineering_log_blocks(text)
    query_records: list[tuple[str, str]] = []
    for ts, tr, ans in blocks:
        if ts.date() != day:
            continue
        if ans.strip() == UNKNOWN_QUERY_REPLY.strip():
            continue
        query_records.append((tr, ans))
    if not query_records:
        print(f"No telemetry query entries found in {log_path} for {day.isoformat()}.")
        return
    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base_url,
        timeout=openai_timeout_sec,
    )
    summary = summarize_query_session_for_engineering_log(
        client=client,
        query_records=query_records,
        summary_model=summary_model,
    )
    if not summary:
        print("Model returned an empty session summary; not writing to log.")
        return
    summary = format_rollup_summary_numbered(summary)
    append_session_roll_up(log_path, summary)
    print(f"Session roll-up appended to {log_path} ({len(query_records)} queries summarized).")


def save_wav(frames: list, path: Path) -> None:
    """Save list of raw PCM frames (bytes) to WAV file."""
    raw = b"".join(frames)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(raw)


def run_realtime_demo(
    openai_api_key: str,
    openai_api_base_url: str | None,
    openai_timeout_sec: float,
    silence_sec: float,
    min_speech_sec: float,
    asr_model: str,
    stt_language: str | None,
    stt_prompt: str | None,
    summary_model: str,
    intent_model: str,
    log_path: Path,
    telemetry_root: Path,
    default_scenario: str,
    debug: bool = False
) -> None:
    """Main loop: record -> VAD -> transcribe -> intent query only -> append log."""
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad

    vad_model = load_silero_vad()
    openai_client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base_url,
        timeout=openai_timeout_sec,
    )

    silence_threshold_frames = int(silence_sec * 1000 / FRAME_DURATION_MS)
    min_speech_frames = int(min_speech_sec * 1000 / FRAME_DURATION_MS)
    vad_window_samples = int(SAMPLE_RATE * SILERO_WINDOW_MS / 1000)
    vad_tail_samples = int(SAMPLE_RATE * SILERO_TAIL_MS / 1000)

    print("=" * 50)
    print("JPL ASTRA - Real-time STT Demo")
    print("=" * 50)
    print(f"OpenAI base URL: {openai_api_base_url or 'https://api.openai.com/v1'}")
    print(f"OpenAI timeout: {openai_timeout_sec:.1f}s")
    print(f"ASR model: {asr_model}")
    print(f"STT language hint: {stt_language or '(auto)'}")
    print(f"Summary model: {summary_model}")
    print(f"Intent model: {intent_model}")
    print(f"Telemetry root: {telemetry_root.resolve()}")
    print(f"Default scenario: {default_scenario}")
    print(f"Engineering log: {log_path.resolve()}")
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"Silence to trigger: {silence_sec}s | Min speech: {min_speech_sec}s")
    print("Press Ctrl+C to quit.")
    print("=" * 50)

    speech_frames = []
    silence_frames = 0
    in_speech = False
    vad_buffer = np.zeros(0, dtype=np.float32)

    def audio_callback(indata, frames, time_info, status):
        nonlocal speech_frames, silence_frames, in_speech, vad_buffer
        if status:
            print(f"[Audio] {status}", file=sys.stderr)
        # indata is (frames, channels), float32 in [-1, 1]
        # Convert to int16 for WAV/transport compatibility
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        # Process in 30ms chunks
        for i in range(0, len(pcm), FRAME_SIZE):
            chunk_i16 = pcm[i : i + FRAME_SIZE]
            if len(chunk_i16) < FRAME_SIZE:
                break
            chunk = chunk_i16.tobytes()
            chunk_f32 = chunk_i16.astype(np.float32) / 32768.0

            vad_buffer = np.concatenate((vad_buffer, chunk_f32))
            if vad_buffer.size > vad_window_samples:
                vad_buffer = vad_buffer[-vad_window_samples:]

            speech_timestamps = get_speech_timestamps(
                torch.from_numpy(vad_buffer.copy()),
                vad_model,
                sampling_rate=SAMPLE_RATE,
                threshold=SILERO_THRESHOLD,
                min_speech_duration_ms=100,
                min_silence_duration_ms=80,
                speech_pad_ms=30,
            )
            recent_boundary = max(0, vad_buffer.size - vad_tail_samples)
            is_speech = any(ts["end"] > recent_boundary for ts in speech_timestamps)

            if is_speech:
                speech_frames.append(chunk)
                silence_frames = 0
                in_speech = True
            elif in_speech:
                speech_frames.append(chunk)
                silence_frames += 1

    def process_utterance():
        nonlocal speech_frames, silence_frames, in_speech
        if len(speech_frames) < min_speech_frames:
            return
        frames_to_process = list(speech_frames)
        speech_frames.clear()
        silence_frames = 0
        in_speech = False
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            save_wav(frames_to_process, tmp_path)
            duration = len(frames_to_process) * FRAME_DURATION_MS / 1000
            print(f"\n  [Processing {duration:.1f}s of audio...]")
            transcript = transcribe_with_openai(
                openai_client,
                tmp_path,
                asr_model,
                stt_language=stt_language,
                stt_prompt=stt_prompt,
            )
            segments = []
            if transcript.strip():
                if is_likely_hallucination(transcript, segments, debug=debug):
                    print("  >>> (noise / no actual content)")
                else:
                    print(f"  >>> {transcript}")
                    answer = answer_from_transcript(
                        client=openai_client,
                        transcript=transcript,
                        intent_model=intent_model,
                        telemetry_root=telemetry_root,
                        default_scenario=default_scenario,
                    )
                    print(f"  [ASTRA] {answer}")
                    append_engineering_log(log_path, transcript, answer)
                    print("  [Engineering log updated]")
            else:
                print("  >>> (no speech detected)")
        except Exception as e:
            print(f"  [Error] {e}")
        finally:
            tmp_path.unlink(missing_ok=True)

    # Stream: process when silence threshold reached
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=FRAME_SIZE,
            callback=audio_callback,
        ):
            while True:
                sd.sleep(100)
                if in_speech and silence_frames >= silence_threshold_frames:
                    process_utterance()
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Real-time STT Quick Demo")
    parser.add_argument("--openai-api-key", default=None, help="OpenAI API Key (default: from OPENAI_API_KEY)")
    parser.add_argument(
        "--openai-api-base-url",
        default=DEFAULT_OPENAI_BASE_URL,
        help=f"OpenAI base URL (default: {DEFAULT_OPENAI_BASE_URL or 'https://api.openai.com/v1'})",
    )
    parser.add_argument(
        "--openai-timeout-sec",
        type=float,
        default=DEFAULT_OPENAI_TIMEOUT_SECONDS,
        help=f"Timeout for OpenAI calls in seconds (default: {DEFAULT_OPENAI_TIMEOUT_SECONDS})",
    )
    parser.add_argument("--asr-model", default=DEFAULT_ASR_MODEL, help=f"OpenAI ASR model (default: {DEFAULT_ASR_MODEL})")
    parser.add_argument(
        "--stt-language",
        default=DEFAULT_STT_LANGUAGE,
        help=f"STT language hint, e.g. en/zh (default: {DEFAULT_STT_LANGUAGE or 'auto-detect'})",
    )
    parser.add_argument(
        "--stt-prompt",
        default=DEFAULT_STT_PROMPT,
        help="Optional priming prompt for transcription bias",
    )
    parser.add_argument(
        "--summary-model",
        default=DEFAULT_SUMMARY_MODEL,
        help=f"OpenAI summary model (default: {DEFAULT_SUMMARY_MODEL})"
    )
    parser.add_argument(
        "--intent-model",
        default=DEFAULT_INTENT_MODEL,
        help=f"OpenAI intent parser model (default: {DEFAULT_INTENT_MODEL})"
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=Path(DEFAULT_LOG_PATH),
        help=f"Engineering log output path (default: {DEFAULT_LOG_PATH})"
    )
    parser.add_argument(
        "--telemetry-root",
        type=Path,
        default=Path(DEFAULT_TELEMETRY_ROOT),
        help=f"Telemetry dataset root directory (default: {DEFAULT_TELEMETRY_ROOT})"
    )
    parser.add_argument(
        "--default-scenario",
        default=DEFAULT_SCENARIO,
        help=f"Default telemetry scenario if not inferred (default: {DEFAULT_SCENARIO})"
    )
    parser.add_argument(
        "--silence-sec", type=float, default=DEFAULT_SILENCE_SEC,
        help="Seconds of silence to trigger transcription (default: 1.5)"
    )
    parser.add_argument(
        "--min-speech-sec", type=float, default=DEFAULT_MIN_SPEECH_SEC,
        help="Min speech duration to process, shorter chunks ignored (default: 0.45)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Print confidence values (no_speech_prob, avg_logprob) when filtering"
    )
    parser.add_argument(
        "--clear-log",
        action="store_true",
        help="Reset the engineering log file (truncate to header) and exit.",
    )
    parser.add_argument(
        "--finalize-session",
        action="store_true",
        help=(
            "Do not open the microphone. Read engineering_log.md, take today's successful "
            "telemetry query entries, append one session roll-up summary (for when the operator "
            "ends a voice session after queries; same hook a future frontend can call)."
        ),
    )
    parser.add_argument(
        "--finalize-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="With --finalize-session, roll up queries for this local calendar day (default: today)",
    )
    args = parser.parse_args()

    if args.clear_log:
        if not args.log_path.exists():
            args.log_path.write_text("# ASTRA Engineering Log\n", encoding="utf-8")
        else:
            args.log_path.write_text("# ASTRA Engineering Log\n", encoding="utf-8")
        print(f"Engineering log reset: {args.log_path}")
        return

    openai_api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Missing OpenAI API key. Provide --openai-api-key or set OPENAI_API_KEY.")
        sys.exit(1)

    if args.finalize_session:
        session_dt: datetime | None = None
        if args.finalize_date:
            try:
                session_dt = datetime.strptime(args.finalize_date.strip(), "%Y-%m-%d")
            except ValueError:
                print("--finalize-date must be YYYY-MM-DD")
                sys.exit(1)
        run_finalize_session(
            openai_api_key=openai_api_key,
            openai_api_base_url=args.openai_api_base_url,
            openai_timeout_sec=args.openai_timeout_sec,
            summary_model=args.summary_model,
            log_path=args.log_path,
            session_date=session_dt,
        )
        return

    # Check dependencies (not required for --finalize-session)
    try:
        import sounddevice
        import numpy
        import torch
        import silero_vad
    except ImportError:
        print("Missing dependency. Install with:")
        print("  python -m pip install -r requirements.txt")
        sys.exit(1)

    run_realtime_demo(
        openai_api_key=openai_api_key,
        openai_api_base_url=args.openai_api_base_url,
        openai_timeout_sec=args.openai_timeout_sec,
        silence_sec=args.silence_sec,
        min_speech_sec=args.min_speech_sec,
        asr_model=args.asr_model,
        stt_language=args.stt_language,
        stt_prompt=args.stt_prompt,
        summary_model=args.summary_model,
        intent_model=args.intent_model,
        log_path=args.log_path,
        telemetry_root=args.telemetry_root,
        default_scenario=args.default_scenario,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
