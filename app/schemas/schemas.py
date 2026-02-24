"""
Pydantic Schemas - API request/response formats
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ Enums ============

class SessionStatus(str, Enum):
    active = "active"
    ended  = "ended"


class NoteType(str, Enum):
    observation = "observation"
    command     = "command"
    system      = "system"


# ============ Session Schemas ============

class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class SessionUpdate(BaseModel):
    name:        Optional[str]           = None
    description: Optional[str]           = None
    status:      Optional[SessionStatus] = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          str
    name:        str
    description: Optional[str]
    status:      SessionStatus
    started_at:  datetime
    ended_at:    Optional[datetime]


# ============ Note Schemas ============

class NoteCreate(BaseModel):
    timestamp:          datetime
    speaker:            Optional[str]            = None
    content:            str
    type:               NoteType                 = NoteType.observation
    tags:               List[str]                = Field(default_factory=list)
    telemetry_snapshot: Optional[Dict[str, Any]] = None


class NoteUpdate(BaseModel):
    content: Optional[str]       = None
    speaker: Optional[str]       = None
    type:    Optional[NoteType]  = None
    tags:    Optional[List[str]] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 str
    session_id:         str
    timestamp:          datetime
    speaker:            Optional[str]
    content:            str
    type:               NoteType
    tags:               List[str]
    telemetry_snapshot: Optional[Dict[str, Any]]
    created_at:         datetime
    updated_at:         datetime


# ============ Telemetry Schemas ============

class TelemetryCreate(BaseModel):
    timestamp: datetime
    channel:   str
    value:     float
    unit:      Optional[str] = None


class TelemetryBatchCreate(BaseModel):
    data: List[TelemetryCreate]


class TelemetryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         str
    session_id: str
    timestamp:  datetime
    channel:    str
    value:      float
    unit:       Optional[str]


# ============ STT Task Schemas ============

class STTTaskCreate(BaseModel):
    """POST /api/sessions/{sid}/stt/tasks"""
    audio_chunk_id:   str
    duration_seconds: Optional[float] = None


class STTTaskUpdate(BaseModel):
    """PUT /api/sessions/{sid}/stt/tasks/{tid}"""
    status:     str
    transcript: Optional[str] = None
    error:      Optional[str] = None


class STTTaskResponse(BaseModel):
    """STT task response object"""
    model_config = ConfigDict(from_attributes=True)

    id:               str
    session_id:       str
    audio_chunk_id:   str
    duration_seconds: Optional[float]
    status:           str
    transcript:       Optional[str]
    error:            Optional[str]
    created_at:       datetime
    updated_at:       datetime


# ============ WebSocket Schemas ============

class WebSocketMessage(BaseModel):
    event:      str
    session_id: str
    data:       Dict[str, Any]
