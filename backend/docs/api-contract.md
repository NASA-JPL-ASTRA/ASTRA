# ASTRA API Contract

**Version:** 0.2.0  
**Base URL:** `http://localhost:8000`  
**Last Updated:** February 2025

---

> **Who is this for?**
> - **Frontend Team ** — Sessions, Notes read/edit/export, Telemetry channels, WebSocket subscription
> - **AI/Data Team ** — POST notes, STT task lifecycle, telemetry latest value

---

## General Rules

- All timestamps must be **ISO 8601 UTC** format: `2025-01-26T10:32:15Z`
- All requests/responses use **JSON** (`Content-Type: application/json`)
- Session ID (`sid`) is required in the URL path for all session-scoped endpoints
- A `404` is returned if the session or resource does not exist

---

## 1. Sessions API

### POST `/api/sessions` — Create Session

**Called by:** Frontend (when operator starts a new test run)

**Request Body:**
```json
{
  "name": "Motor Test Session #42",
  "description": "Testing CADRE rover arm torque limits"
}
```

**Response `200`:**
```json
{
  "id": "sess_a1b2c3d4",
  "name": "Motor Test Session #42",
  "description": "Testing CADRE rover arm torque limits",
  "status": "active",
  "started_at": "2025-01-26T10:00:00Z",
  "ended_at": null
}
```

---

### GET `/api/sessions` — List Sessions

**Called by:** Frontend (dashboard view)

**Response `200`:** Array of session objects (newest first)

---

### GET `/api/sessions/{sid}` — Get Session

**Called by:** Frontend

**Response `200`:** Single session object

---

### PATCH `/api/sessions/{sid}` — Update Session

**Called by:** Frontend (e.g., end session when test is done)

**Request Body (all fields optional):**
```json
{
  "name": "Updated Session Name",
  "description": "Updated description",
  "status": "ended"
}
```

> Setting `status: "ended"` automatically records `ended_at` timestamp.

**Status values:** `active` | `ended`

---

## 2. Notes API

### POST `/api/sessions/{sid}/notes` — Create Note

**Called by: AI/Data Module** (after Whisper transcribes + LLM processes audio chunk)

**Request Body:**
```json
{
  "timestamp": "2025-01-26T10:32:15Z",
  "speaker": "Engineer A",
  "content": "Motor current rising to 2.3A, temperature looks stable.",
  "type": "observation",
  "tags": ["motor", "current"],
  "telemetry_snapshot": {
    "battery_voltage": 32.5,
    "motor_current": 2.3
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `timestamp` | ISO datetime | ✅ | When observation was made |
| `speaker` | string | ❌ | e.g. "Engineer A" — from diarization or device label |
| `content` | string | ✅ | The note text |
| `type` | enum | ❌ | `observation` (default) / `command` / `system` |
| `tags` | string[] | ❌ | Keywords for filtering, defaults to `[]` |
| `telemetry_snapshot` | object | ❌ | Optional key-value of relevant telemetry at that moment |

**Response `200`:** Full note object with generated `id`, `created_at`, `updated_at`

**Side effect:** Broadcasts `note.created` to all WebSocket clients on this session.

---

### GET `/api/sessions/{sid}/notes` — List Notes

**Called by:** Frontend

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `speaker` | string | Filter by speaker name |
| `type` | enum | Filter by `observation` / `command` / `system` |
| `from` | ISO datetime | Notes at or after this time |
| `to` | ISO datetime | Notes at or before this time |

**Example:**
```
GET /api/sessions/sess_abc/notes?speaker=Engineer A&type=observation
```

**Response `200`:** Array of note objects, sorted by `timestamp` ascending.

---

### GET `/api/sessions/{sid}/notes/export` — Export Notes

**Called by:** Frontend (export button)

**Query Parameters:**

| Param | Values | Default |
|-------|--------|---------|
| `format` | `markdown` / `json` | `markdown` |

**Markdown response** — ready to copy/paste into JPL test logs, Confluence, etc.  
**JSON response** — structured export for programmatic use.

---

### GET `/api/sessions/{sid}/notes/{note_id}` — Get Note

**Called by:** Frontend

---

### PUT `/api/sessions/{sid}/notes/{note_id}` — Edit Note

**Called by:** Frontend (operator manually corrects AI-generated note)

**Request Body (all fields optional):**
```json
{
  "content": "Motor current rising to 2.5A (operator correction)",
  "speaker": "Engineer B",
  "type": "observation",
  "tags": ["motor", "current", "corrected"]
}
```

**Response `200`:** Updated note object.

**Side effect:** Broadcasts `note.updated` to all WebSocket clients.

---

### DELETE `/api/sessions/{sid}/notes/{note_id}` — Delete Note

**Called by:** Frontend

**Response `200`:**
```json
{ "message": "Note note_abc123 deleted" }
```

**Side effect:** Broadcasts `note.deleted` to all WebSocket clients.

---

## 3. Telemetry API

### POST `/api/sessions/{sid}/telemetry` — Ingest Single

**Called by:** Telemetry Source

```json
{
  "timestamp": "2025-01-26T10:32:15Z",
  "channel": "battery_voltage",
  "value": 32.5,
  "unit": "V"
}
```

---

### POST `/api/sessions/{sid}/telemetry/batch` — Batch Ingest

**Called by:** Telemetry Source

```json
{
  "data": [
    { "timestamp": "...", "channel": "battery_voltage", "value": 32.5, "unit": "V" },
    { "timestamp": "...", "channel": "motor_current",   "value": 2.3,  "unit": "A" }
  ]
}
```

**Response:** `{ "created": 2 }`

---

### GET `/api/sessions/{sid}/telemetry` — Query Telemetry

**Called by:** Frontend, AI Module

| Param | Type | Description |
|-------|------|-------------|
| `channel` | string | Filter by channel name |
| `from` | ISO datetime | Filter from time |
| `to` | ISO datetime | Filter to time |
| `limit` | int | Max records (default: 1000) |

Returns records sorted newest-first.

---

### GET `/api/sessions/{sid}/telemetry/latest?channel=X` — Get Latest Value

**Called by: AI Module**

Used when operator says *"ASTRA, log the current voltage"* — AI calls this endpoint, gets the live value, and attaches it to a note via `telemetry_snapshot`.

**Example:**
```
GET /api/sessions/sess_abc/telemetry/latest?channel=battery_voltage
```

**Response `200`:** Single telemetry object with most recent value.

---

### GET `/api/sessions/{sid}/telemetry/channels` — List Channels

**Called by:** Frontend

**Response `200`:**
```json
{ "channels": ["battery_voltage", "motor_current", "temperature"] }
```

---

## 4. STT Tasks API *(New in v0.2.0)*

Manages the lifecycle of speech-to-text audio chunks. Follows the sponsor-approved **pause-based segmentation workflow**.

### Workflow Summary
```
Frontend detects pause → AI Module registers task → Whisper processes → AI Module updates task → Backend broadcasts result
```

---

### POST `/api/sessions/{sid}/stt/tasks` — Register STT Task

**Called by: AI/Data Module** (when a new audio chunk is ready for processing)

**Request Body:**
```json
{
  "audio_chunk_id": "chunk_20250126_001",
  "duration_seconds": 8.4
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `audio_chunk_id` | string | ✅ | Your internal reference for the audio file |
| `duration_seconds` | float | ❌ | Length of the audio segment |

**Response `201`:**
```json
{
  "id": "stt_f1e2d3c4",
  "session_id": "sess_abc123",
  "audio_chunk_id": "chunk_20250126_001",
  "duration_seconds": 8.4,
  "status": "pending",
  "transcript": null,
  "error": null,
  "created_at": "2025-01-26T10:32:15Z",
  "updated_at": "2025-01-26T10:32:15Z"
}
```

**Side effect:** Broadcasts `stt.task.created` via WebSocket.

---

### GET `/api/sessions/{sid}/stt/tasks` — List Tasks

**Called by:** Frontend (to show transcription history / status indicators)

Returns all tasks for this session, sorted newest-first.

---

### GET `/api/sessions/{sid}/stt/tasks/{tid}` — Get Task

**Called by:** Frontend / AI Module (to poll status)

---

### PUT `/api/sessions/{sid}/stt/tasks/{tid}` — Update Task Result

**Called by: AI/Data Module** (when Whisper finishes processing)

**On success:**
```json
{
  "status": "done",
  "transcript": "Motor current rising to 2.3 amps, temperature looks stable.",
  "error": null
}
```

**On failure:**
```json
{
  "status": "failed",
  "transcript": null,
  "error": "Audio too short or no speech detected"
}
```

**Side effects:**
- `status: done` → broadcasts `stt.task.done` via WebSocket
- `status: failed` → broadcasts `error.occurred` via WebSocket

---

## 5. WebSocket

### WS `/ws/sessions/{sid}` — Subscribe to Session Events

**Called by:** Frontend (connect on session open, disconnect on session end)

#### Connection
```js
const ws = new WebSocket("ws://localhost:8000/ws/sessions/sess_abc123");
```

#### Keep-Alive
Send `"ping"` → server responds `"pong"`.

#### Event Reference

All events:
```json
{
  "event": "<event_type>",
  "session_id": "sess_abc123",
  "data": { ... }
}
```

| Event | When | `data` contains |
|-------|------|-----------------|
| `connected` | On successful connection | `{ "message": "Connected to session sess_abc123" }` |
| `note.created` | AI posts a new note | Full note object |
| `note.updated` | Operator edits a note | Updated note object |
| `note.deleted` | Note is deleted | `{ "id": "note_xxx" }` |
| `stt.task.created` | AI registers audio chunk | STT task object (status: pending) |
| `stt.task.done` | Whisper transcript ready | STT task object (status: done, transcript filled) |
| `error.occurred` | STT failed or system error | `{ "message": "...", "source": "stt" }` |

#### Frontend Usage Example
```js
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  switch (msg.event) {
    case "note.created":
      appendNoteToUI(msg.data);
      break;
    case "note.updated":
      updateNoteInUI(msg.data);
      break;
    case "note.deleted":
      removeNoteFromUI(msg.data.id);
      break;
    case "stt.task.done":
      showTranscriptChunk(msg.data.transcript);
      break;
    case "error.occurred":
      showErrorBanner(msg.data.message);
      break;
  }
};
```

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `404` | Session, note, telemetry channel, or STT task not found |
| `422` | Request body validation failed (check field types/formats) |
| `500` | Internal server error |

**Example 404:**
```json
{ "detail": "Session sess_xyz not found" }
```

---

## Quick Reference: Who Calls What

| Endpoint | Frontend | AI/Data Module |
|----------|----------|----------------|
| POST `/sessions` | ✅ | |
| GET/PATCH `/sessions` | ✅ | |
| POST `/notes` | | ✅ |
| GET/PUT/DELETE `/notes` | ✅ | |
| GET `/notes/export` | ✅ | |
| POST `/telemetry` (ingest) | | ✅ |
| GET `/telemetry` (query) | ✅ | ✅ |
| GET `/telemetry/latest` | | ✅ |
| POST `/stt/tasks` | | ✅ |
| GET `/stt/tasks` | ✅ | |
| PUT `/stt/tasks/{tid}` | | ✅ |
| WS `/ws/sessions/{sid}` | ✅ (subscribe) | |
