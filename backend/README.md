# Backend

**Advanced System for Testbed Recording and Analysis**  
Capstone Project — Backend Service (v0.2.0)

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
# venv\Scripts\activate    # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn app.main:app --reload

# 4. Open browser
# API Docs (Swagger): http://localhost:8000/docs
# Health:             http://localhost:8000/health
```

---

## Project Structure

```
astra-backend/
├── app/
│   ├── main.py                 # FastAPI app entry point, CORS, router registration
│   ├── database.py             # In-memory storage (dev/test) — will migrate to PostgreSQL
│   ├── ws_manager.py           # Centralized WebSocket broadcast + event type constants
│   ├── routes/
│   │   ├── sessions.py         # Session lifecycle (create/list/get/update)
│   │   ├── notes.py            # Notes CRUD + export (Markdown/JSON)
│   │   ├── telemetry.py        # Telemetry ingestion & query
│   │   ├── stt.py              # STT task lifecycle (NEW in v0.2.0)
│   │   └── websocket.py        # WebSocket subscribe endpoint
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic request/response models
│   └── models/
│       └── __init__.py         # Placeholder for future SQLAlchemy models
├── docs/
│   ├── api-contract.md         # Full API contract for Frontend + AI/Data team
│   └── frontend-integration.md # Step-by-step integration guide for Frontend
├── smoke_test.py               # End-to-end API validation script
├── websocket_test.html         # Browser-based WebSocket test UI
├── requirements.txt
└── README.md
```

---

## API Endpoints Overview

### Sessions — `/api/sessions`

| Method | Endpoint | Description | Called By |
|--------|----------|-------------|-----------|
| POST | `/api/sessions` | Create new session | Frontend |
| GET | `/api/sessions` | List all sessions | Frontend |
| GET | `/api/sessions/{sid}` | Get specific session | Frontend |
| PATCH | `/api/sessions/{sid}` | Update metadata / end session | Frontend |

### Notes — `/api/sessions/{sid}/notes`

| Method | Endpoint | Description | Called By |
|--------|----------|-------------|-----------|
| POST | `/{sid}/notes` | Create note | **AI/Data Module** |
| GET | `/{sid}/notes` | List notes (filters: speaker, type, from/to) | Frontend |
| GET | `/{sid}/notes/export` | Export as Markdown or JSON | Frontend |
| GET | `/{sid}/notes/{id}` | Get specific note | Frontend |
| PUT | `/{sid}/notes/{id}` | Edit note (operator correction) | Frontend |
| DELETE | `/{sid}/notes/{id}` | Delete note | Frontend |

### Telemetry — `/api/sessions/{sid}/telemetry`

| Method | Endpoint | Description | Called By |
|--------|----------|-------------|-----------|
| POST | `/{sid}/telemetry` | Ingest single telemetry point | Telemetry Source |
| POST | `/{sid}/telemetry/batch` | Batch ingest | Telemetry Source |
| GET | `/{sid}/telemetry` | Query (filters: channel, from/to) | Frontend / AI |
| GET | `/{sid}/telemetry/latest?channel=X` | Get latest value for a channel | **AI Module** |
| GET | `/{sid}/telemetry/channels` | List available channels | Frontend |

### STT Tasks — `/api/sessions/{sid}/stt/tasks` *(New in v0.2.0)*

| Method | Endpoint | Description | Called By |
|--------|----------|-------------|-----------|
| POST | `/{sid}/stt/tasks` | Register new STT task (audio chunk submitted) | **AI/Data Module** |
| GET | `/{sid}/stt/tasks` | List all tasks for session | Frontend |
| GET | `/{sid}/stt/tasks/{tid}` | Get task status | Frontend / AI |
| PUT | `/{sid}/stt/tasks/{tid}` | Update task result (done / failed) | **AI/Data Module** |

### WebSocket — `/ws/sessions/{sid}`

| Type | Endpoint | Description | Called By |
|------|----------|-------------|-----------|
| WS | `/ws/sessions/{sid}` | Subscribe to real-time session events | Frontend |

---

## WebSocket Events

All events follow the format:
```json
{
  "event": "event.type",
  "session_id": "sess_abc123",
  "data": { ... }
}
```

| Event | Trigger |
|-------|---------|
| `connected` | Client connects successfully |
| `note.created` | New note POSTed |
| `note.updated` | Note PUTted (operator edit) |
| `note.deleted` | Note DELETEd |
| `stt.task.created` | AI team registers a new STT task |
| `stt.task.done` | Whisper transcript ready |
| `error.occurred` | STT task failed or system error |

---

## STT Workflow (v0.2.0)

The sponsor-approved audio processing flow (pause-based segmentation):

```
1. Frontend monitors audio input
2. Detects pause in speech (configurable threshold)
3. Uploads audio chunk to AI/Data Module
4. AI Module calls POST /api/sessions/{sid}/stt/tasks → status: pending
5. AI Module sends chunk to Whisper for processing
6. AI Module calls PUT /api/sessions/{sid}/stt/tasks/{tid} with transcript → status: done
7. Backend broadcasts stt.task.done via WebSocket
8. Frontend displays transcript
9. AI Module optionally POSTs a structured note to /api/sessions/{sid}/notes
```

---

## Data Formats

### Note Object
```json
{
  "id": "note_a1b2c3d4",
  "session_id": "sess_abc123",
  "timestamp": "2025-01-26T10:32:15Z",
  "speaker": "Engineer A",
  "content": "Motor current rising, temperature nominal",
  "type": "observation",
  "tags": ["motor", "current"],
  "telemetry_snapshot": {
    "battery_voltage": 32.5,
    "motor_current": 2.3
  },
  "created_at": "2025-01-26T10:32:16Z",
  "updated_at": "2025-01-26T10:32:16Z"
}
```

Note types: `observation` | `command` | `system`

### Telemetry Object
```json
{
  "id": "tel_x1y2z3w4",
  "session_id": "sess_abc123",
  "timestamp": "2025-01-26T10:32:15Z",
  "channel": "battery_voltage",
  "value": 32.5,
  "unit": "V"
}
```

### STT Task Object
```json
{
  "id": "stt_f1e2d3c4",
  "session_id": "sess_abc123",
  "audio_chunk_id": "chunk_001",
  "duration_seconds": 8.4,
  "status": "done",
  "transcript": "Motor current rising to 2.3 amps, temperature looks stable.",
  "error": null,
  "created_at": "2025-01-26T10:32:15Z",
  "updated_at": "2025-01-26T10:32:17Z"
}
```

Status values: `pending` | `done` | `failed`

---

## Export Notes

```bash
# Export as Markdown (for copy/paste into other systems)
GET /api/sessions/{sid}/notes/export?format=markdown

# Export as JSON (for programmatic use)
GET /api/sessions/{sid}/notes/export?format=json
```

---

## Testing

```bash
# Make sure backend is running first
uvicorn app.main:app --reload

# Run smoke test (validates all endpoints)
python smoke_test.py

# Test WebSocket in browser
open websocket_test.html
```

The smoke test validates: Session CRUD, Notes CRUD + export, Telemetry ingestion + query, WebSocket connectivity.

Expected output: `All tests passed! Backend is ready for integration.`

---

## Development Status

- [x] Session management (CRUD)
- [x] Notes CRUD + Markdown/JSON export
- [x] Telemetry ingestion, query, latest value
- [x] WebSocket real-time push (note events)
- [x] STT task lifecycle API (v0.2.0)
- [x] Centralized WS broadcast + error events (v0.2.0)
- [x] In-memory storage (dev/test)
- [ ] PostgreSQL integration
- [ ] Authentication / operator identity

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.109 |
| Validation | Pydantic v2 |
| WebSocket | FastAPI native |
| Storage | In-memory dict (dev) → PostgreSQL (prod) |
| Runtime | Uvicorn |
