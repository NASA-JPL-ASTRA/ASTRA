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
from datetime import datetime, timezone
from typing import Any, Dict, List

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


def _chat_completion_json(messages: List[Dict[str, str]]) -> Dict[str, Any] | None:
    key = _openai_key()
    if not key:
        return None
    url = f"{_openai_base_url()}/chat/completions"
    payload = {
        "model": _structure_model(),
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
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

    current_payload = {
        "anomalies": [a.model_dump(mode="json") for a in doc.anomalies],
        "detail_paragraphs": [p.model_dump(mode="json") for p in doc.detail_notes.paragraphs],
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You maintain an ASTRA test session structure note. "
                "ALL human-readable fields you write (titles, descriptions, bullet_markdown, "
                "source_transcript_excerpt, user_utterance_raw when you paraphrase) MUST be in English. "
                "Return ONLY JSON (no markdown fences) with keys: "
                '"anomalies" (array), "detail_paragraphs" (array). '
                "Each anomaly: id, recorded_at, user_utterance_raw, title, description, "
                'severity one of info|low|med|high, known_pattern_id (string or null). '
                "Each detail paragraph: id, updated_at, time_anchor, bullet_markdown, "
                "source_transcript_excerpt, source_task_ids (array of strings, may be empty). "
                "All times MUST be ISO 8601 with explicit timezone (use UTC, e.g. 2026-05-07T12:01:16+00:00). "
                "You MAY delete bullets by omitting them. You MAY merge or rewrite freely; "
                "preserve an existing id when updating that item, use a new id only for brand-new items. "
                "Detail bullets should read like concise English meeting notes. "
                "Only add or strengthen anomalies when the user clearly reports an issue; "
                "use request_anomaly_capture hint when true. "
                "For each anomaly: title MUST be a tight bullet headline (≤12 words, ≤90 characters). "
                "description MUST be at most ONE short sentence (≤22 words, ≤160 characters) that "
                "rephrases the concern in test-engineer language — never paste or quote the full "
                "transcript. Do NOT start description with 'The operator asked' or similar filler. "
                "user_utterance_raw must be the exact speaker words for audit (can match new_transcript "
                "for new items). "
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
            doc.detail_notes = DetailNotes(paragraphs=out.detail_paragraphs)
            return _save(doc)
        except Exception as e:
            logger.warning("LLM output validation failed, using fallback: %s", e)

    return _save(_fallback_voice_chunk(doc, t, recorded_at, request_anomaly_capture))


def _fallback_voice_chunk(
    doc: StructureNoteDocument,
    transcript: str,
    recorded_at: str,
    request_anomaly_capture: bool,
) -> StructureNoteDocument:
    if not transcript_qualifies_for_notes(transcript):
        return doc
    text_lower = transcript.lower()
    want_anomaly = request_anomaly_capture or any(
        k in transcript for k in ("問題", "記下來", "異常", "奇怪")
    ) or any(
        k in text_lower
        for k in (
            "please log",
            "log this for me",
            "log this",
            "remember this",
            "anomaly",
            "weird",
            "strange",
            "knocking",
        )
    )

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

    pid = f"para_{uuid.uuid4().hex[:10]}"
    excerpt = transcript[:600] + ("…" if len(transcript) > 600 else "")
    bullet = f"• {recorded_at} — {transcript[:180]}" + ("…" if len(transcript) > 180 else "")
    doc.detail_notes.paragraphs.append(
        DetailParagraph(
            id=pid,
            updated_at=recorded_at,
            time_anchor=recorded_at,
            bullet_markdown=bullet,
            source_transcript_excerpt=excerpt,
        )
    )
    doc.anomalies = _clamp_anomaly_brevity(doc.anomalies)
    return doc


def _offline_test_summary_markdown(
    session_name: str,
    gen_at: str,
    notes: List[dict],
    doc: StructureNoteDocument,
    *,
    session_description: str = "",
    telemetry_mock_test1_path: str | None = None,
) -> str:
    """
    Offline test summary: short synthesized narrative — no transcript paste,
    no UI boilerplate, no duplicate anomaly/detail lists.
    """
    texts = [(n.get("content") or "").strip() for n in notes if (n.get("content") or "").strip()]
    n_notes = len(texts)
    n_detail = len(doc.detail_notes.paragraphs)

    lines: List[str] = []

    purpose_bits: List[str] = [
        "This was an **ASTRA browser voice debrief** tied to the session timeline: "
        "spoken commentary is captured, structured into detail notes, and any explicit "
        "**log / anomaly** requests are lifted into the anomaly panel."
    ]
    if session_description:
        purpose_bits.append(
            f"The session record describes the run as: {session_description[:220]}"
            + ("…" if len(session_description) > 220 else "")
        )
    if telemetry_mock_test1_path:
        purpose_bits.append(
            "A **mock Test 1 straight-line / bumps** telemetry folder was generated in the background "
            "for correlation with this voice timeline (see session telemetry path on the server)."
        )
    lines.append(" ".join(purpose_bits))
    lines.append("")

    if not texts:
        lines.append(
            "No transcript text was captured, so there is nothing to summarize about operator intent. "
            "If that is unexpected, verify microphone permissions and the STT path, then re-run."
        )
        return "\n\n".join(lines)

    lines.append(
        f"The recording produced **{n_notes}** transcript segment(s) and **{n_detail}** "
        "structured detail paragraph(s). Issue flags live only in the **Anomalies** panel, not here."
    )
    lines.append("")
    lines.append(
        "At a high level, this summary describes how voice and optional mock telemetry were used "
        "together for the debrief; use **Detail notes** for time-ordered excerpts and **Anomalies** "
        "for anything explicitly flagged during the run."
    )

    return "\n\n".join(lines)


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


def _offline_auto_update_summary(
    manual_summary: str,
    transcript_segments: List[dict],
    doc: StructureNoteDocument,
) -> str:
    parts: List[str] = []
    if manual_summary.strip():
        parts.append(manual_summary.strip())

    recent = [seg["text"].strip() for seg in transcript_segments[-6:] if seg.get("text")]
    if recent:
        parts.extend(
            [
                "## Recent updates",
                _one_sentence_summary(" ".join(recent), max_words=70, max_chars=420),
            ]
        )

    if doc.detail_notes.paragraphs:
        detail = [
            _one_sentence_summary(detailNote.source_transcript_excerpt or detailNote.bullet_markdown, 22, 160)
            for detailNote in doc.detail_notes.paragraphs[-4:]
        ]
        detail = [line for line in detail if line]
        if detail:
            parts.extend(["## Detail note context", *[f"- {line}" for line in detail]])

    return "\n\n".join(parts).strip() or "No summary content is available yet."


def auto_update_test_summary(session_id: str, manual_summary: str) -> StructureNoteDocument:
    """
    Operator-triggered merge: combine manual summary with current transcript context.
    Unlike session finalization, this is allowed to replace the summary because the
    operator explicitly requested it.
    """
    session = get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    doc = get_or_create_structure_note(session_id)
    protected_manual, protected_images = _protect_markdown_data_images(manual_summary.strip())

    notes = sorted(get_notes_by_session(session_id), key=lambda n: str(n.get("timestamp", "")))
    transcript_segments: List[dict] = []
    for n in notes:
        c = (n.get("content") or "").strip()
        if c:
            transcript_segments.append({"timestamp": str(n.get("timestamp")), "text": c})

    messages = [
        {
            "role": "system",
            "content": (
                "You update a live ASTRA Test summary by merging operator-written notes with "
                "the latest transcript context. Return ONLY JSON with keys: content_markdown "
                "(string), generated_at (string, ISO 8601 with timezone UTC). Preserve the "
                "operator's intent and important wording. Integrate new transcript information "
                "concisely; do not paste raw transcript. Keep Markdown image placeholders such "
                "as [[PASTED_IMAGE_1]] exactly where they belong. Do not remove image placeholders. "
                "Do not include a top-level heading that repeats 'Test summary'. Use English unless "
                "the operator-written notes are primarily another language."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "session_name": session.get("name"),
                    "session_status": session.get("status"),
                    "session_description": (session.get("description") or "").strip(),
                    "manual_summary_markdown": protected_manual,
                    "transcript_segments": transcript_segments,
                    "detail_notes": [
                        {
                            "time_anchor": p.time_anchor,
                            "text": p.source_transcript_excerpt or p.bullet_markdown,
                        }
                        for p in doc.detail_notes.paragraphs[-20:]
                    ],
                    "anomaly_cards": [
                        {"title": a.title, "description": a.description, "severity": a.severity}
                        for a in doc.anomalies
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]

    parsed = _chat_completion_json(messages)
    if parsed is not None:
        try:
            out = TestSummaryLLMOutput.model_validate(parsed)
            content = _restore_markdown_data_images(
                out.content_markdown.strip() or protected_manual,
                protected_images,
            )
            doc.test_summary = TestSummary(
                status=TestSummaryStatus.ready,
                generated_at=out.generated_at or utc_iso_timestamp(),
                content_markdown=content,
                error=None,
            )
            return _save(doc)
        except Exception as e:
            logger.warning("Auto-update summary LLM validation failed: %s", e)

    content = _offline_auto_update_summary(protected_manual, transcript_segments, doc)
    doc.test_summary = TestSummary(
        status=TestSummaryStatus.ready,
        generated_at=utc_iso_timestamp(),
        content_markdown=_restore_markdown_data_images(content, protected_images),
        error=None,
    )
    return _save(doc)


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
    transcript_segments: List[dict] = []
    for n in notes:
        c = (n.get("content") or "").strip()
        if c:
            transcript_segments.append({"timestamp": str(n.get("timestamp")), "text": c})

    messages = [
        {
            "role": "system",
            "content": (
                "You write the final TEST SUMMARY for a completed ASTRA recording session. "
                "Use **English only**. "
                "Return ONLY JSON with keys: content_markdown (string), generated_at (string, "
                "ISO 8601 with timezone, UTC e.g. 2026-05-07T12:01:16+00:00). "
                "Write **2 to 5 paragraphs** of plain prose in markdown (use **bold** sparingly for emphasis). "
                "Do **not** include a top-level heading that repeats 'Test summary' — the UI already shows that title. "
                "Explain in your own words what this session was for: **voice debrief** plus optional "
                "**mock telemetry** correlation when mentioned in context. "
                "Do **not** paste, quote, or lightly shuffle long stretches of transcript_segments — "
                "summarize intent, flow, and outcome at a high level only. "
                "Do **not** enumerate individual anomaly_cards, do **not** count them, and do **not** "
                "paste anomaly titles or descriptions — the Anomalies panel is the source of truth. "
                "Do **not** add UI boilerplate (e.g. 'this section is narrative only', 'not duplicated below'). "
                "Do **not** use bullet lists of every utterance."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "session_name": session.get("name"),
                    "session_description": (session.get("description") or "").strip(),
                    "telemetry_mock_test1_path": session.get("telemetry_mock_test1_path"),
                    "transcript_segments": transcript_segments,
                    "detail_note_paragraph_count": len(doc.detail_notes.paragraphs),
                    "anomaly_cards": [
                        {"title": a.title, "description": a.description} for a in doc.anomalies
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]

    parsed = _chat_completion_json(messages)
    if parsed is not None:
        try:
            out = TestSummaryLLMOutput.model_validate(parsed)
            gen_at = out.generated_at or utc_iso_timestamp()
            doc.test_summary = TestSummary(
                status=TestSummaryStatus.ready,
                generated_at=gen_at,
                content_markdown=out.content_markdown.strip() or "(empty summary)",
            )
            _save(doc)
            return
        except Exception as e:
            logger.warning("Test summary LLM validation failed: %s", e)

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
