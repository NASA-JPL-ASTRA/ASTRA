"""
Structure note generation: voice-chunk merge (anomalies + detail notes) and
session-end test summary. Uses OpenAI Chat Completions when OPENAI_API_KEY
is set; otherwise deterministic fallbacks so the stack runs offline.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.database import get_notes_by_session, get_session, structure_notes_db
from app.services.transcript_quality import transcript_qualifies_for_notes
from app.schemas.structure_note import (
    AnomalyItem,
    AnomalySeverity,
    DetailParagraph,
    DetailNotes,
    StructureNoteDocument,
    StructureNoteLLMOutput,
    TestSummary,
    TestSummaryLLMOutput,
    TestSummaryStatus,
    document_from_storage,
    document_to_storage_dict,
    empty_structure_note,
)

logger = logging.getLogger(__name__)

_ANOMALY_TRIGGER_PREFIXES_EN = (
    "please log this:",
    "please log this",
    "log this for me:",
    "log this for me",
    "log this:",
    "log this",
    "remember this:",
    "remember this",
)
_ANOMALY_TRIGGER_MARKERS_ZH = ("記下來", "幫我記", "請記", "請記錄")

# Offline fallback: time-based merge only when topic match is ambiguous.
_DETAIL_SEGMENT_GAP_SECONDS = 180

# Heuristic topic buckets so the same theme merges into one detail bullet (offline + post-LLM).
_DETAIL_TOPIC_GROUPS: List[tuple[tuple[str, ...], str]] = [
    (("motor", "temperature", "thermal", "overheat", "over heat"), "motor_thermal"),
    (("rear-right", "rear right", "rear wheel"), "rear_drive"),
    (("debris", "loose ground", "low gear", "rut"), "terrain_debris"),
    (("traction", "slip", "spinning", "grip", "immobil"), "traction"),
    (("suspension", "uneven", "bump"), "suspension"),
    (("basin", "ridge", "rocky", "terrain transition", "route"), "route_terrain"),
    (("solar", "array", "sunlight", "sun-point"), "power_solar"),
    (("imu", "encoder", "sensor", "telemetry"), "sensors_telemetry"),
    (("battery", "voltage", "current", "power"), "power_electrical"),
]

# Offline fallback only — operational concern cues (never the word "anomaly" alone).
_OFFLINE_ISSUE_CUE_RE = re.compile(
    r"(?:"
    r"\btoo\s+hot\b|\boverheat|\bover\s*heat|\bfailed\b|\bfailure\b|\berror\b|\bfault\b|"
    r"\bnot\s+working\b|\bdropped?\s+out\b|\bunstable\b|\bway\s+too\b|"
    r"\bmight\s+need\s+to\s+be\s+aware\b|\bneed\s+to\s+be\s+aware\b|"
    r"\b(seems?|looks?)\s+like\b.{0,40}\b(hot|high|low|wrong|off|bad)\b|"
    r"\b(strange|weird)\b.{0,30}\b(noise|sound|behavior|behaviour|vibrat)\b|"
    r"\bknocking\b|問題|異常|奇怪"
    r")",
    re.IGNORECASE,
)


def explicit_log_request(transcript: str) -> bool:
    """True when the speaker explicitly asks to log/remember an issue (not mere mention of 'anomaly')."""
    text = transcript.strip()
    if not text:
        return False
    head = text[:32]
    if any(marker in head for marker in _ANOMALY_TRIGGER_MARKERS_ZH):
        return True
    tl = text.lower()
    return any(
        phrase in tl
        for phrase in (
            "please log this",
            "please log",
            "log this for me",
            "log this",
            "remember this",
            "mark this",
        )
    )


def utterance_describes_operational_issue(transcript: str) -> bool:
    """
    Offline-only: rough cue that the speaker is reporting a test issue.
    Does NOT treat the word 'anomaly' by itself as an issue report.
    """
    text = transcript.strip()
    if not text:
        return False
    if explicit_log_request(text):
        return True
    tl = text.lower()
    if re.search(r"\banomal(?:y|ies)\b", tl):
        if re.search(r"\b(mark|log|record|capture|note)\b", tl):
            return True
        return False
    return _OFFLINE_ISSUE_CUE_RE.search(text) is not None


def _strip_anomaly_request_prefix(transcript: str) -> str:
    """Remove common 'log this' prefixes so title/description focus on the issue."""
    t = transcript.strip()
    tl = t.lower()
    for p in _ANOMALY_TRIGGER_PREFIXES_EN:
        if tl.startswith(p):
            return t[len(p) :].strip()
    head = t[:24]
    for marker in _ANOMALY_TRIGGER_MARKERS_ZH:
        if marker in head:
            idx = t.find(marker)
            if idx >= 0:
                return (t[idx + len(marker) :]).strip()
    return t


def _one_sentence_summary(text: str, max_words: int = 18, max_chars: int = 140) -> str:
    """Very short paraphrase-style line for offline anomaly description."""
    words = re.split(r"\s+", text.strip())
    words = [w for w in words if w]
    if not words:
        return ""
    snippet = " ".join(words[:max_words]).strip()
    if len(snippet) > max_chars:
        cut = snippet[: max_chars - 1]
        shorter = cut.rsplit(" ", 1)[0].strip()
        snippet = (shorter or cut) + "…"
    return snippet


def _fallback_anomaly_title_and_description(transcript: str) -> tuple[str, str]:
    core = _strip_anomaly_request_prefix(transcript).strip() or transcript.strip()
    line = core.split("\n")[0].strip()
    if not line:
        line = transcript.strip()[:120]
    # Short headline (bullet-style), not a transcript echo
    title = _one_sentence_summary(line, max_words=10, max_chars=72)
    if len(title) < 6:
        title = "Voice-reported issue"
    # Single tight sentence; no "operator asked" boilerplate, no full paste
    desc = _one_sentence_summary(core, max_words=22, max_chars=140)
    if len(desc) < 12:
        desc = _one_sentence_summary(transcript.strip(), max_words=18, max_chars=120)
    if len(desc) < 8:
        desc = "Flagged during debrief for follow-up."
    return title, desc


def utc_iso_timestamp() -> str:
    """UTC as standard ISO 8601 with explicit offset, e.g. 2026-05-07T12:01:16+00:00."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _openai_base_url() -> str:
    return (os.getenv("OPENAI_API_BASE_URL") or "https://api.openai.com/v1").rstrip("/")


def _openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _structure_model() -> str:
    return os.getenv("OPENAI_STRUCTURE_NOTE_MODEL", "gpt-5.5")


def _model_supports_temperature(model: str) -> bool:
    """GPT-5 / o-series reasoning models reject non-default temperature (API 400)."""
    m = model.strip().lower()
    if not m:
        return True
    if "chat-latest" in m:
        return True
    if m.startswith(("o1", "o3", "o4")):
        return False
    if m.startswith("gpt-5"):
        return False
    return True


def _chat_completion_json(messages: List[Dict[str, str]]) -> Dict[str, Any] | None:
    key = _openai_key()
    if not key:
        return None
    model = _structure_model()
    url = f"{_openai_base_url()}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    if _model_supports_temperature(model):
        payload["temperature"] = 0.2
    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        content = _strip_json_fence(content)
        return json.loads(content)
    except Exception as e:
        logger.exception("OpenAI structure-note call failed: %s", e)
        return None


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def get_or_create_structure_note(session_id: str) -> StructureNoteDocument:
    if session_id not in structure_notes_db:
        doc = empty_structure_note(session_id, utc_iso_timestamp())
        structure_notes_db[session_id] = document_to_storage_dict(doc)
    return document_from_storage(structure_notes_db[session_id])


def _save(doc: StructureNoteDocument) -> StructureNoteDocument:
    doc.updated_at = utc_iso_timestamp()
    structure_notes_db[doc.session_id] = document_to_storage_dict(doc)
    return doc


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def resolve_chunk_time_anchor(
    session_id: str,
    *,
    utterance_start_ms: Optional[float] = None,
    fallback_iso: str,
) -> str:
    """Map recording-relative ms to session ISO time when possible."""
    if utterance_start_ms is None:
        return fallback_iso
    session = get_session(session_id)
    if not session:
        return fallback_iso
    started = session.get("started_at")
    if isinstance(started, str):
        started_dt = _parse_iso_datetime(started)
    elif isinstance(started, datetime):
        started_dt = started if started.tzinfo else started.replace(tzinfo=timezone.utc)
    else:
        return fallback_iso
    if started_dt is None:
        return fallback_iso
    anchor = started_dt + timedelta(milliseconds=float(utterance_start_ms))
    return anchor.isoformat(timespec="seconds")


def _detail_topic_key(text: str) -> Optional[str]:
    """Best-effort topic id for merging detail bullets about the same theme."""
    tl = text.lower()
    best_key: Optional[str] = None
    best_score = 0
    for keywords, key in _DETAIL_TOPIC_GROUPS:
        score = sum(1 for kw in keywords if kw in tl)
        if score > best_score:
            best_score = score
            best_key = key
    return best_key if best_score > 0 else None


def _fallback_detail_summary(transcript: str) -> str:
    """Detail-note line: slightly more technical length than test summary."""
    line = transcript.strip().split("\n")[0].strip() or transcript.strip()
    summary = _one_sentence_summary(line, max_words=70, max_chars=460)
    if len(summary) < 20:
        summary = _one_sentence_summary(transcript.strip(), max_words=65, max_chars=440)
    return summary or "Voice debrief topic."


def _merge_detail_paragraph_group(group: List[DetailParagraph]) -> DetailParagraph:
    ordered = sorted(group, key=lambda p: (p.time_anchor or p.updated_at or ""))
    base = ordered[0]
    combined = " ".join((p.bullet_markdown or "").strip() for p in ordered if (p.bullet_markdown or "").strip())
    bullet = _one_sentence_summary(combined, max_words=80, max_chars=480) or combined[:480]
    excerpts = " ".join((p.source_transcript_excerpt or "").strip() for p in ordered)
    excerpt = excerpts[:400] + ("…" if len(excerpts) > 400 else "")
    return base.model_copy(
        update={
            "bullet_markdown": bullet,
            "source_transcript_excerpt": excerpt,
            "updated_at": ordered[-1].updated_at,
        }
    )


def _consolidate_detail_paragraphs(paragraphs: List[DetailParagraph]) -> List[DetailParagraph]:
    """One bullet per session topic — merge duplicates by thematic keyword overlap."""
    if len(paragraphs) <= 1:
        return paragraphs

    buckets: Dict[str, List[DetailParagraph]] = {}
    unlabeled: List[DetailParagraph] = []
    for p in paragraphs:
        text = f"{p.bullet_markdown or ''} {p.source_transcript_excerpt or ''}"
        key = _detail_topic_key(text)
        if key:
            buckets.setdefault(key, []).append(p)
        else:
            unlabeled.append(p)

    merged: List[DetailParagraph] = [_merge_detail_paragraph_group(g) for g in buckets.values()]
    merged.extend(unlabeled)

    def sort_key(p: DetailParagraph) -> datetime:
        dt = _parse_iso_datetime(p.time_anchor or p.updated_at or "")
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    merged.sort(key=sort_key)
    return merged


def _looks_like_verbatim_dump(summary: str, raw: str) -> bool:
    s = summary.strip().lower()
    r = raw.strip().lower()
    if not s or not r:
        return False
    if s == r:
        return True
    if len(s) >= 80 and (s in r or r.startswith(s[: min(len(s), 120)])):
        return True
    return False


def _sanitize_detail_paragraphs(
    paragraphs: List[DetailParagraph],
    *,
    latest_raw: str = "",
) -> List[DetailParagraph]:
    """Ensure detail segments are condensed summaries, not full transcript dumps."""
    out: List[DetailParagraph] = []
    for p in paragraphs:
        raw = (p.source_transcript_excerpt or latest_raw or "").strip()
        bullet = (p.bullet_markdown or "").strip()
        bullet = re.sub(r"^\s*[•\-*]\s*", "", bullet)
        bullet = re.sub(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*(?:[—:\-]\s*)?",
            "",
            bullet,
            count=1,
            flags=re.IGNORECASE,
        ).strip()
        if (
            not bullet
            or len(bullet) > 500
            or _looks_like_verbatim_dump(bullet, raw or bullet)
        ):
            bullet = _fallback_detail_summary(raw or bullet)
        if len(bullet) > 480:
            bullet = bullet[:477] + "…"
        excerpt = raw[:400] + ("…" if len(raw) > 400 else "") if raw else ""
        anchor = (p.time_anchor or p.updated_at or utc_iso_timestamp()).strip()
        out.append(
            p.model_copy(
                update={
                    "time_anchor": anchor,
                    "bullet_markdown": bullet,
                    "source_transcript_excerpt": excerpt,
                }
            )
        )
    return out


def _merge_or_append_detail_paragraph(
    doc: StructureNoteDocument,
    *,
    time_anchor: str,
    summary: str,
    raw_excerpt: str,
    recorded_at: str,
) -> None:
    """Offline: merge by topic first; otherwise merge within a short time window."""
    paragraphs = doc.detail_notes.paragraphs
    topic = _detail_topic_key(f"{summary} {raw_excerpt}")

    if topic and paragraphs:
        for idx, existing in enumerate(paragraphs):
            existing_text = f"{existing.bullet_markdown or ''} {existing.source_transcript_excerpt or ''}"
            if _detail_topic_key(existing_text) == topic:
                prev = (existing.bullet_markdown or "").strip()
                merged = _one_sentence_summary(
                    f"{prev} {summary}".strip(),
                    max_words=80,
                    max_chars=480,
                )
                excerpt = ((existing.source_transcript_excerpt or "") + " " + raw_excerpt).strip()
                excerpt = excerpt[:400] + ("…" if len(excerpt) > 400 else "")
                paragraphs[idx] = existing.model_copy(
                    update={
                        "updated_at": recorded_at,
                        "bullet_markdown": merged or summary,
                        "source_transcript_excerpt": excerpt,
                    }
                )
                return

    anchor_dt = _parse_iso_datetime(time_anchor)
    if paragraphs and anchor_dt is not None:
        last = paragraphs[-1]
        last_dt = _parse_iso_datetime(last.time_anchor or last.updated_at or "")
        if last_dt is not None:
            gap = (anchor_dt - last_dt).total_seconds()
            if 0 <= gap <= _DETAIL_SEGMENT_GAP_SECONDS:
                prev = (last.bullet_markdown or "").strip()
                merged = _one_sentence_summary(
                    f"{prev} {summary}".strip(),
                    max_words=80,
                    max_chars=480,
                )
                excerpt = (last.source_transcript_excerpt or "") + " " + raw_excerpt
                excerpt = excerpt.strip()[:400] + ("…" if len(excerpt) > 400 else "")
                paragraphs[-1] = last.model_copy(
                    update={
                        "updated_at": recorded_at,
                        "bullet_markdown": merged or summary,
                        "source_transcript_excerpt": excerpt,
                    }
                )
                return

    pid = f"para_{uuid.uuid4().hex[:10]}"
    paragraphs.append(
        DetailParagraph(
            id=pid,
            updated_at=recorded_at,
            time_anchor=time_anchor,
            bullet_markdown=summary,
            source_transcript_excerpt=raw_excerpt[:400] + ("…" if len(raw_excerpt) > 400 else ""),
        )
    )


def _clamp_anomaly_brevity(items: List[AnomalyItem]) -> List[AnomalyItem]:
    """Keep anomaly titles/descriptions short bullet-style after LLM output."""
    out: List[AnomalyItem] = []
    for a in items:
        t = (a.title or "").strip()
        d = (a.description or "").strip()
        if len(t) > 88:
            t = t[:85] + "…"
        if len(d) > 160:
            d = d[:157] + "…"
        out.append(a.model_copy(update={"title": t or "Issue", "description": d}))
    return out


def apply_voice_chunk(
    session_id: str,
    transcript: str,
    *,
    request_anomaly_capture: bool,
    utterance_start_ms: Optional[float] = None,
    chunk_time_anchor: Optional[str] = None,
) -> StructureNoteDocument:
    """
    Merge one transcript chunk into anomalies + detail_notes using LLM if available.
    LLM may delete or rewrite any prior bullets (full replacement of the two lists).
    """
    doc = get_or_create_structure_note(session_id)
    recorded_at = utc_iso_timestamp()
    t = transcript.strip()
    if not transcript_qualifies_for_notes(t):
        return doc

    time_anchor = (chunk_time_anchor or "").strip() or resolve_chunk_time_anchor(
        session_id,
        utterance_start_ms=utterance_start_ms,
        fallback_iso=recorded_at,
    )

    current_payload = {
        "anomalies": [a.model_dump(mode="json") for a in doc.anomalies],
        "detail_paragraphs": [p.model_dump(mode="json") for p in doc.detail_notes.paragraphs],
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You maintain an ASTRA test session structure note. "
                "ALL human-readable fields you write (titles, descriptions, bullet_markdown) "
                "MUST be in English. user_utterance_raw keeps exact speaker words for audit. "
                "Return ONLY JSON (no markdown fences) with keys: "
                '"anomalies" (array), "detail_paragraphs" (array). '
                "Each anomaly: id, recorded_at, user_utterance_raw, title, description, "
                'severity one of info|low|med|high, known_pattern_id (string or null). '
                "Each detail paragraph: id, updated_at, time_anchor, bullet_markdown, "
                "source_transcript_excerpt, source_task_ids (array of strings, may be empty). "
                "All times MUST be ISO 8601 with explicit timezone (use UTC, e.g. 2026-05-07T12:01:16+00:00). "
                "You MAY delete bullets by omitting them. You MAY merge or rewrite freely; "
                "preserve an existing id when updating that item, use a new id only for brand-new items. "
                "ANOMALIES — always use semantic judgment, independent of logging commands: "
                "Whenever new_transcript describes an equipment problem, out-of-spec reading, safety concern, "
                "unexpected behavior, or follow-up needed, you MUST add or update an anomaly — even if the "
                "speaker never says 'log this', '記下來', or 'anomaly'. "
                "Examples that MUST become anomalies: motors running too hot; encoder dropouts; IMU drift. "
                "Do NOT add an anomaly only because the word 'anomaly' appears without a concrete issue. "
                "request_anomaly_capture true means the speaker also asked to log something — still capture "
                "the underlying issue; it is NOT required for you to create anomalies. "
                "For each anomaly: title = tight headline (≤12 words). description = one short sentence "
                "(≤22 words) in test-engineer language — never paste the full transcript. "
                "DETAIL NOTES — TOPIC INDEX for the session (not a timeline of every utterance): "
                "detail_paragraphs has ONE entry per distinct thematic topic discussed in the whole session "
                "(typically ~3–8 topics, not one per STT chunk). Ordered oldest→newest by time_anchor. "
                "time_anchor = when that topic FIRST came up (keep earliest when merging). "
                "If new_transcript continues an existing topic, UPDATE that paragraph (same id) — even minutes later. "
                "Do NOT create a second bullet for the same theme (e.g. motor temperature repeated → one bullet). "
                "bullet_markdown = 2–4 sentences: high-level but MORE technical than the Test summary — include "
                "subsystems, sensor/telemetry context, procedures, and qualitative readings when spoken. "
                "Example: 'Operators review rear-right motor thermal telemetry during ridge ascent; temperatures "
                "trend high and workload redistribution is considered to avoid critical overheat. Live channel "
                "data is compared against expected nominal range.' "
                "NEVER paste full new_transcript verbatim. Max ~480 characters per bullet. "
                "source_transcript_excerpt = optional audit snippet (≤200 characters). "
                "Issues that belong in Anomalies should not be duplicated here unless needed for topic context. "
                "If new_transcript looks like ASR noise (random fragments, not deliberate test speech), "
                "return the same anomalies and detail_paragraphs arrays as in the input unchanged."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "session_id": session_id,
                    "recorded_at_for_new_items": recorded_at,
                    "chunk_time_anchor": time_anchor,
                    "utterance_start_ms": utterance_start_ms,
                    "request_anomaly_capture": request_anomaly_capture,
                    "new_transcript": t,
                    "current_anomalies_and_detail_paragraphs": current_payload,
                },
                ensure_ascii=False,
            ),
        },
    ]

    parsed = _chat_completion_json(messages)
    if parsed is not None:
        try:
            out = StructureNoteLLMOutput.model_validate(parsed)
            doc.anomalies = _clamp_anomaly_brevity(out.anomalies)
            doc.detail_notes = DetailNotes(
                paragraphs=_consolidate_detail_paragraphs(
                    _sanitize_detail_paragraphs(
                        out.detail_paragraphs,
                        latest_raw=t,
                    )
                )
            )
            return _save(doc)
        except Exception as e:
            logger.warning("LLM output validation failed, using fallback: %s", e)

    return _save(
        _fallback_voice_chunk(
            doc,
            t,
            recorded_at,
            request_anomaly_capture,
            time_anchor=time_anchor,
        )
    )


def _fallback_voice_chunk(
    doc: StructureNoteDocument,
    transcript: str,
    recorded_at: str,
    request_anomaly_capture: bool,
    *,
    time_anchor: str,
) -> StructureNoteDocument:
    if not transcript_qualifies_for_notes(transcript):
        return doc
    want_anomaly = request_anomaly_capture or utterance_describes_operational_issue(transcript)

    if want_anomaly:
        aid = f"anom_{uuid.uuid4().hex[:10]}"
        atitle, adesc = _fallback_anomaly_title_and_description(transcript)
        doc.anomalies.append(
            AnomalyItem(
                id=aid,
                recorded_at=recorded_at,
                user_utterance_raw=transcript,
                title=atitle,
                description=adesc,
                severity=AnomalySeverity.med,
            )
        )

    summary = _fallback_detail_summary(transcript)
    _merge_or_append_detail_paragraph(
        doc,
        time_anchor=time_anchor,
        summary=summary,
        raw_excerpt=transcript,
        recorded_at=recorded_at,
    )
    doc.detail_notes = DetailNotes(
        paragraphs=_consolidate_detail_paragraphs(
            _sanitize_detail_paragraphs(doc.detail_notes.paragraphs, latest_raw=transcript)
        )
    )
    doc.anomalies = _clamp_anomaly_brevity(doc.anomalies)
    return doc


_SETUP_META_RE = re.compile(
    r"(voice\s*meeter|backend\s+stt|speech[- ]to[- ]text|browser\s+microphon|"
    r"dual\s+voice|structured\s+detail\s+notes|anomalies\s+panel|live\s+transcription|"
    r"REC-\d{8}-\d{6}|with\s+backend\s+stt)",
    re.IGNORECASE,
)


def _session_description_is_setup_meta(description: str) -> bool:
    """True when session description is tooling/routing metadata, not test content."""
    desc = description.strip()
    if not desc:
        return True
    return bool(_SETUP_META_RE.search(desc))


def _sentence_is_setup_meta(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return True
    if _SETUP_META_RE.search(s):
        return True
    sl = s.lower()
    return bool(
        re.search(r"\bwas conducted as\b", sl)
        or re.search(r"\bthe session\s+REC-", sl)
        or re.search(r"\bsession\s+REC-", sl)
        or re.search(r"\busing backend\b", sl)
        or re.search(r"\bsingle\s+.+\s+input test\b", sl)
    )


def _strip_test_summary_setup_prose(markdown: str) -> str:
    """Remove sentences about REC ids, VoiceMeeter, STT pipeline, etc."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", markdown.strip()) if p.strip()]
    kept: List[str] = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        good = [s for s in sentences if s.strip() and not _sentence_is_setup_meta(s)]
        if good:
            kept.append(" ".join(good))
    return "\n\n".join(kept)


_TEST_SUMMARY_SYSTEM = (
    "You write the Test summary for an ASTRA voice debrief session. "
    "Return ONLY JSON with keys: content_markdown (string), generated_at (ISO 8601 UTC). "
    "content_markdown MUST be 1 to 3 paragraphs of plain English prose only. "
    "Separate paragraphs with a blank line. You may use **bold** sparingly. "
    "Do NOT use headings (#), bullet lists, numbered lists, or markdown tables. "
    "Paragraph 1: operational purpose of the test/run (what the team was doing), from speech only. "
    "Paragraph 2: what happened during the run (synthesized narrative). "
    "Paragraph 3 (optional): outcome, end state, or next steps. "
    "Synthesize from transcript_segments; never paste long verbatim quotes. "
    "NEVER mention recording IDs (REC-…), session names, VoiceMeeter, microphones, backend STT, "
    "browser capture, ASTRA UI, or other tooling/setup — internal_metadata is not for the summary. "
    "Do NOT paraphrase session_description when it describes infrastructure rather than the test. "
    "Do NOT list anomalies, severity tables, detail-note timestamps, key-event bullets, "
    "or duplicate Anomalies / Detail notes panel content. "
    "anomaly_count and detail_segment_count are background only — do not enumerate them. "
    "If session_in_progress is true, summarize what is known so far without inventing facts. "
    "Incorporate manual_summary_markdown when provided (skip setup-only lines there too). "
    "Do not include a title repeating 'Test summary'. Use English unless manual notes are primarily another language."
)


def _collect_transcript_segments(notes: List[dict]) -> List[dict]:
    segments: List[dict] = []
    for note in notes:
        text = _strip_transcript_timestamps(str(note.get("content") or ""))
        if text:
            segments.append(
                {
                    "speaker": str(note.get("speaker") or "Unknown"),
                    "text": text,
                }
            )
    return segments


def _build_test_summary_user_payload(
    session: dict,
    doc: StructureNoteDocument,
    transcript_segments: List[dict],
    manual_markdown: str,
    *,
    session_in_progress: bool,
) -> Dict[str, Any]:
    desc = (session.get("description") or "").strip()
    return {
        "session_in_progress": session_in_progress,
        "manual_summary_markdown": manual_markdown,
        "transcript_segments": transcript_segments,
        "anomaly_count": len(doc.anomalies),
        "detail_segment_count": len(doc.detail_notes.paragraphs),
        "internal_metadata_do_not_quote": {
            "session_name": session.get("name"),
            "session_status": session.get("status"),
            "session_description": desc,
        },
        "operational_context_only": (
            desc if desc and not _session_description_is_setup_meta(desc) else ""
        ),
    }


def _sanitize_test_summary_markdown(markdown: str) -> str:
    """Strip headings, lists, and tables the LLM should not emit in Test summary."""
    text = _strip_live_transcript_updates(markdown.strip())
    if not text:
        return text

    cleaned_lines: List[str] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped[1:]:
            in_table = True
            continue
        if in_table:
            if not stripped:
                in_table = False
            continue
        if re.match(r"^#{1,6}\s", stripped):
            continue
        if re.match(r"^[\-*•]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) > 3:
        paragraphs = paragraphs[:3]
    text = "\n\n".join(paragraphs)
    return _strip_test_summary_setup_prose(text)


def _synthesize_offline_test_summary(
    session: dict,
    notes: List[dict],
    doc: StructureNoteDocument,
    manual_markdown: str,
) -> str:
    """1–3 paragraph offline summary (no anomaly/detail duplication)."""
    segments = _collect_transcript_segments(notes)
    desc = (session.get("description") or "").strip()
    manual_clean = _sanitize_test_summary_markdown(_strip_live_transcript_updates(manual_markdown))

    if not segments:
        para1 = (
            "Transcript capture is still in progress; no spoken test content is available to summarize yet."
            if session.get("status") != "ended"
            else "No usable spoken content was captured to summarize this run."
        )
        paras = [para1]
        if manual_clean:
            paras.insert(0, manual_clean)
        return "\n\n".join(paras)

    combined = " ".join(seg["text"] for seg in segments)
    if desc and not _session_description_is_setup_meta(desc):
        para1 = _one_sentence_summary(desc, max_words=40, max_chars=260)
    else:
        head = " ".join(seg["text"] for seg in segments[:3])
        para1 = _one_sentence_summary(head, max_words=55, max_chars=320)
    para2 = _one_sentence_summary(combined, max_words=95, max_chars=560)
    paras = [p for p in [para1, para2] if p.strip()]
    if len(segments) >= 4:
        tail = " ".join(seg["text"] for seg in segments[-3:])
        para3 = _one_sentence_summary(tail, max_words=50, max_chars=300)
        if para3:
            paras.append(para3)
    if manual_clean and manual_clean not in paras:
        paras.insert(1, manual_clean)
    return _sanitize_test_summary_markdown("\n\n".join(paras))


def _generate_test_summary_via_llm(
    session: dict,
    doc: StructureNoteDocument,
    transcript_segments: List[dict],
    manual_markdown: str,
    *,
    session_in_progress: bool,
) -> Optional[TestSummary]:
    if not _openai_key():
        return None
    messages = [
        {"role": "system", "content": _TEST_SUMMARY_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(
                _build_test_summary_user_payload(
                    session,
                    doc,
                    transcript_segments,
                    manual_markdown,
                    session_in_progress=session_in_progress,
                ),
                ensure_ascii=False,
            ),
        },
    ]
    parsed = _chat_completion_json(messages)
    if parsed is None:
        return None
    try:
        out = TestSummaryLLMOutput.model_validate(parsed)
        content = _sanitize_test_summary_markdown(
            out.content_markdown.strip() or manual_markdown.strip() or "(empty summary)"
        )
        return TestSummary(
            status=TestSummaryStatus.ready,
            generated_at=out.generated_at or utc_iso_timestamp(),
            content_markdown=content,
            error=None,
        )
    except Exception as e:
        logger.warning("Test summary LLM validation failed: %s", e)
        return None


def _offline_test_summary_markdown(
    session_name: str,
    gen_at: str,
    notes: List[dict],
    doc: StructureNoteDocument,
    *,
    session_description: str = "",
    telemetry_mock_test1_path: str | None = None,
) -> str:
    """Offline test summary used at session end when LLM is unavailable."""
    session_stub = {
        "name": session_name,
        "description": session_description,
        "status": "ended",
        "telemetry_mock_test1_path": telemetry_mock_test1_path,
    }
    body = _synthesize_offline_test_summary(session_stub, notes, doc, "")
    return _sanitize_test_summary_markdown(body)


_DATA_IMAGE_MD_RE = re.compile(
    r"!\[[^\]\r\n]*\]\(data:image/(?:png|jpe?g|gif|webp);base64,[^)]+\)",
    re.IGNORECASE,
)


def _protect_markdown_data_images(markdown: str) -> tuple[str, Dict[str, str]]:
    images: Dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f"[[PASTED_IMAGE_{len(images) + 1}]]"
        images[token] = match.group(0)
        return token

    return _DATA_IMAGE_MD_RE.sub(replace, markdown), images


def _restore_markdown_data_images(markdown: str, images: Dict[str, str]) -> str:
    out = markdown
    missing: List[str] = []
    for token, image_markdown in images.items():
        if token in out:
            out = out.replace(token, image_markdown)
        elif image_markdown not in out:
            missing.append(image_markdown)
    if missing:
        out = f"{out.rstrip()}\n\n" + "\n\n".join(missing)
    return out.strip()


def _strip_live_transcript_updates(markdown: str) -> str:
    cleaned = re.sub(
        r"(^|\n)#{2,6}\s+Live transcript updates\s*\n.*?(?=\n#{1,6}\s+\S|\Z)",
        "\n",
        markdown.strip(),
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _strip_transcript_timestamps(text: str) -> str:
    """
    Remove timestamp prefixes from transcript text while preserving speaker labels.
    Handles existing auto-update lines such as "- [2026-...] Speaker: text" and
    common ASR timestamp forms such as "[00:01:23] text".
    """
    bracketed_timestamp = (
        r"\[(?:"
        r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
        r"|(?:\d{1,2}:){1,2}\d{1,2}(?:\.\d+)?"
        r")\]"
    )
    cleaned = re.sub(
        rf"(^|\n)(\s*[-*]\s+){bracketed_timestamp}\s+([^:\n]{{1,80}}:\s*)",
        r"\1\2\3",
        text,
    )
    cleaned = re.sub(
        rf"(^|\n)(\s*){bracketed_timestamp}\s+",
        r"\1\2",
        cleaned,
    )
    cleaned = re.sub(
        r"(^|\n)(\s*[-*]\s+)(?:\d{1,2}:){1,2}\d{1,2}(?:\.\d+)?\s+",
        r"\1\2",
        cleaned,
    )
    cleaned = re.sub(
        r"(^|\n)(\s*)(?:\d{1,2}:){1,2}\d{1,2}(?:\.\d+)?\s+",
        r"\1\2",
        cleaned,
    )
    return cleaned.strip()


def _format_live_transcript_lines(transcript_segments: List[dict]) -> List[str]:
    lines: List[str] = []
    for seg in transcript_segments:
        speaker = str(seg.get("speaker") or "Unknown").strip() or "Unknown"
        text = _strip_transcript_timestamps(str(seg.get("text") or ""))
        if not text:
            continue
        lines.append(f"- {speaker}: {text}")
    return lines


def _notes_after_cursor(notes: List[dict], since_note_id: str | None) -> List[dict]:
    if not since_note_id:
        return notes
    for idx, note in enumerate(notes):
        if str(note.get("id")) == since_note_id:
            return notes[idx + 1 :]
    return notes


def auto_update_test_summary(
    session_id: str,
    manual_summary: str,
    since_note_id: str | None = None,
) -> tuple[StructureNoteDocument, str | None, int]:
    """
    Operator-triggered Test summary refresh: always 1–3 prose paragraphs (purpose,
    process, outcome). Uses full transcript so far; same format while recording or ended.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    doc = get_or_create_structure_note(session_id)
    is_ended = session.get("status") == "ended"
    manual_for_update = (
        _strip_live_transcript_updates(manual_summary)
        if is_ended
        else manual_summary.strip()
    )
    protected_manual, protected_images = _protect_markdown_data_images(manual_for_update)

    notes = sorted(get_notes_by_session(session_id), key=lambda n: str(n.get("timestamp", "")))
    last_note_id = str(notes[-1].get("id")) if notes else since_note_id
    notes_to_process = notes if is_ended else _notes_after_cursor(notes, since_note_id)
    processed_count = len(notes_to_process)

    all_segments = _collect_transcript_segments(notes)

    if not all_segments and not protected_manual.strip():
        doc.test_summary = TestSummary(
            status=TestSummaryStatus.ready,
            generated_at=utc_iso_timestamp(),
            content_markdown=doc.test_summary.content_markdown
            or "No transcript has been captured yet for this session.",
            error=None,
        )
        return _save(doc), last_note_id, processed_count

    llm_summary = _generate_test_summary_via_llm(
        session,
        doc,
        all_segments,
        protected_manual,
        session_in_progress=not is_ended,
    )
    if llm_summary is not None:
        llm_summary.content_markdown = _restore_markdown_data_images(
            llm_summary.content_markdown,
            protected_images,
        )
        doc.test_summary = llm_summary
        return _save(doc), last_note_id, processed_count

    content = _synthesize_offline_test_summary(session, notes, doc, protected_manual)
    doc.test_summary = TestSummary(
        status=TestSummaryStatus.ready,
        generated_at=utc_iso_timestamp(),
        content_markdown=_restore_markdown_data_images(content, protected_images),
        error=None,
    )
    return _save(doc), last_note_id, processed_count


def finalize_session_structure_note(session_id: str) -> None:
    """
    Called when recording session ends. Fills test_summary only (anomalies/detail unchanged).
    """
    session = get_session(session_id)
    if not session:
        logger.warning("finalize_session_structure_note: missing session %s", session_id)
        return
    if session.get("status") != "ended":
        return

    doc = get_or_create_structure_note(session_id)
    if doc.test_summary.status == TestSummaryStatus.ready and doc.test_summary.content_markdown.strip():
        logger.info("finalize_session_structure_note: preserving operator summary for %s", session_id)
        return

    doc.test_summary.status = TestSummaryStatus.generating
    doc.test_summary.error = None
    _save(doc)

    notes = sorted(get_notes_by_session(session_id), key=lambda n: str(n.get("timestamp", "")))
    all_segments = _collect_transcript_segments(notes)

    llm_summary = _generate_test_summary_via_llm(
        session,
        doc,
        all_segments,
        "",
        session_in_progress=False,
    )
    if llm_summary is not None:
        doc.test_summary = llm_summary
        _save(doc)
        return

    # Fallback summary (English narrative only; no duplicate sections)
    gen_at = utc_iso_timestamp()
    doc.test_summary = TestSummary(
        status=TestSummaryStatus.ready,
        generated_at=gen_at,
        content_markdown=_offline_test_summary_markdown(
            str(session.get("name") or session_id),
            gen_at,
            notes,
            doc,
            session_description=str(session.get("description") or "").strip(),
            telemetry_mock_test1_path=session.get("telemetry_mock_test1_path"),
        ),
    )
    _save(doc)
