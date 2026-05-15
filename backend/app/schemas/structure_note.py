"""
Structure Note contract (draft v0.1).

User-facing timestamps use standard ISO 8601 with explicit timezone
(UTC recommended), e.g. 2026-05-07T12:01:16+00:00.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestSummaryStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    ready = "ready"
    skipped = "skipped"
    error = "error"


class AnomalySeverity(str, Enum):
    info = "info"
    low = "low"
    med = "med"
    high = "high"


class TelemetryRef(BaseModel):
    """Optional link from an anomaly to a log row."""

    scenario: Optional[str] = None
    log: Optional[str] = Field(None, description="event | channel")
    time: Optional[str] = Field(None, description="ISO 8601 with timezone, e.g. 2026-05-07T12:01:16+00:00")


class AnomalyItem(BaseModel):
    id: str
    recorded_at: str = Field(..., description="ISO 8601 with timezone (UTC recommended)")
    user_utterance_raw: str = ""
    title: str = ""
    description: str = ""
    severity: AnomalySeverity = AnomalySeverity.info
    merge_of: List[str] = Field(default_factory=list)
    related_telemetry_refs: List[TelemetryRef] = Field(default_factory=list)
    known_pattern_id: Optional[str] = None


class DetailParagraph(BaseModel):
    id: str
    updated_at: str = Field(..., description="ISO 8601 with timezone (UTC recommended)")
    time_anchor: str = Field(..., description="ISO 8601 with timezone (UTC recommended)")
    bullet_markdown: str
    source_transcript_excerpt: str = ""
    source_task_ids: List[str] = Field(default_factory=list)


class DetailNotes(BaseModel):
    paragraphs: List[DetailParagraph] = Field(default_factory=list)


class TestSummary(BaseModel):
    status: TestSummaryStatus = TestSummaryStatus.pending
    generated_at: Optional[str] = Field(None, description="ISO 8601 with timezone (UTC recommended)")
    content_markdown: str = ""
    error: Optional[str] = None


class StructureNoteDocument(BaseModel):
    schema_version: str = "0.1"
    session_id: str
    updated_at: str = Field(..., description="ISO 8601 with timezone (UTC recommended)")
    telemetry_time_format: str = Field(
        default="ISO 8601 with timezone (e.g. 2026-05-07T12:01:16+00:00)",
    )
    test_summary: TestSummary = Field(default_factory=TestSummary)
    anomalies: List[AnomalyItem] = Field(default_factory=list)
    detail_notes: DetailNotes = Field(default_factory=DetailNotes)


class VoiceChunkRequest(BaseModel):
    """After each recording chunk: send transcript; backend merges into structure note."""

    transcript: str = Field(..., min_length=1)
    request_anomaly_capture: bool = Field(
        default=False,
        description="True when user asked to log an issue / anomaly (e.g. 幫我記下來).",
    )


class TestSummaryUpdateRequest(BaseModel):
    """Operator-approved replacement for the generated test summary."""

    content_markdown: str = Field(..., min_length=1)


class TestSummaryAutoUpdateRequest(BaseModel):
    """Merge operator-written summary with the latest transcript/context."""

    manual_summary: str = ""
    mode: str = "merge"


class StructureNoteLLMOutput(BaseModel):
    """Validated shape returned by the LLM for voice-chunk updates."""

    anomalies: List[AnomalyItem] = Field(default_factory=list)
    detail_paragraphs: List[DetailParagraph] = Field(default_factory=list)


class TestSummaryLLMOutput(BaseModel):
    content_markdown: str = ""
    generated_at: Optional[str] = None


def empty_structure_note(session_id: str, updated_at_iso: str) -> StructureNoteDocument:
    return StructureNoteDocument(
        session_id=session_id,
        updated_at=updated_at_iso,
        test_summary=TestSummary(status=TestSummaryStatus.pending),
        anomalies=[],
        detail_notes=DetailNotes(paragraphs=[]),
    )


def document_to_storage_dict(doc: StructureNoteDocument) -> Dict[str, Any]:
    return doc.model_dump(mode="json")


def document_from_storage(data: Dict[str, Any]) -> StructureNoteDocument:
    return StructureNoteDocument.model_validate(data)
