# AiSTRA API Contract

**Version:** 0.3.0
**Base URL:** `http://localhost:8000`
**Last Updated:** May 2026

---

> **Who is this for?**
> - **Frontend Team** — Sessions, Notes read/edit/export, Telemetry channels, WebSocket subscription
> - **AI/Data Team** — POST notes (with type), PATCH notes (anomaly append), STT task lifecycle, telemetry queries

---

## What changed in v0.3.0

| Change | Detail |
|--------|--------|
| Note types updated | `observation/command/system` → `detail/anomaly/summary` |
| PATCH endpoint added | `PATCH /notes/{id}` — append content to existing anomaly |
| Session response | Now includes `note_count` field |
| Export format | Markdown export groups notes by type: Summary → Anomalies → Detailed Notes |
| WebSocket event | New `note.appended` event for anomaly append |

---

## General Rules

- All timestamps must be **ISO 8601 UTC** format: `2026-05-04T10:32:15Z`
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
  "started_at": "2026-05-04T10:00:00Z",
  "ended_at": null,
  "note_count": 0
}
```

---

### GET `/api/sessions` — List Sessions

**Called by:** Frontend (dashboard view)

**Response `200`:** Array of session objects (newest first), each with `note_count`.

---

### GET `/api/sessions/{sid}` — Get Session

**Called by:** Frontend

**Response `200`:** Single session object with `note_count`.

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

### Note Types (sponsor wk14)

| Type | When created | Realtime? | Append? | Description |
|------|-------------|-----------|---------|-------------|
| `detail` (default) | Continuously during session | Yes | No — new bullet for new topic | Distilled play-by-play. LLM compresses ~5min of audio into a few sentences with timestamp. |
| `anomaly` | Operator says "this is an anomaly" | Yes | Yes — PATCH to append | Tracked issues. May recur across the session; LLM appends new observations to existing anomaly. |
| `summary` | Session end | No | No | Executive summary generated once by LLM from all detail + anomaly notes. |

> **Who classifies?** The AI module (LLM) decides the type. Backend just stores whatever type the AI module sends.

---

### POST `/api/sessions/{sid}/notes` — Create Note

**Called by: AI/Data Module** (after LLM processes transcription)

**Request Body:**
```json
{
  "timestamp": "2026-05-04T10:32:15Z",
  "speaker": "Engineer A",
  "content": "Drove rover around obstacle rock. Motor current peaked at 2.3A during turn.",
  "type": "detail",
  "tags": ["motor", "driving"],
  "telemetry_snapshot": {
    "motor_current": 2.3,
    "battery_voltage": 32.5
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `timestamp` | ISO datetime | ✅ | When observation was made |
| `speaker` | string | ❌ | e.g. "Engineer A" — from diarization or device label |
| `content` | string | ✅ | The note text |
| `type` | enum | ❌ | `detail` (default) / `anomaly` / `summary` |
| `tags` | string[] | ❌ | Keywords for filtering, defaults to `[]` |
| `telemetry_snapshot` | object | ❌ | Key-value of relevant telemetry at that moment |

**Anomaly example:**
```json
{
  "timestamp": "2026-05-04T11:15:00Z",
  "speaker": "Engineer B",
  "content": "Motor producing unusual vibration noise during arm extension.",
  "type": "anomaly",
  "tags": ["motor", "vibration", "arm"]
}
```

**Summary example (session end):**
```json
{
  "timestamp": "2026-05-04T17:00:00Z",
  "content": "Session completed 12 drive tests and 5 arm tests. Two anomalies tracked: motor vibration during arm extension and intermittent GPS signal loss.",
  "type": "summary"
}
```

**Response `200`:** Full note object with generated `id`, `created_at`, `updated_at`

**Side effect:** Broadcasts `note.created` to all WebSocket clients on this session.

---

### GET `/api/sessions/{sid}/notes` — List Notes

**Called by:** Frontend

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `speaker` | string | Filter by speaker name |
| `type` | enum | Filter by `detail` / `anomaly` / `summary` |
| `from` | ISO datetime | Notes at or after this time |
| `to` | ISO datetime | Notes at or before this time |

**Examples:**
```
GET /api/sessions/sess_abc/notes?type=anomaly
GET /api/sessions/sess_abc/notes?type=detail&from=2026-05-04T10:00:00Z
```

**Response `200`:** Array of note objects, sorted by `timestamp` ascending.

---

### GET `/api/sessions/{sid}/notes/export` — Export Notes

**Called by:** Frontend (export button)

**Query Parameters:**

| Param | Values | Default |
|-------|--------|---------|
| `format` | `markdown` / `json` | `markdown` |

**Markdown output** is grouped by type:
```markdown
# Motor Test Session #42

**Session ID:** sess_abc
**Started:** 2026-05-04T10:00:00Z
**Status:** ended

---

## Test Summary

Session completed 12 drive tests...

---

## Anomalies

### Anomaly #1 [11:15:00]

Motor producing unusual vibration noise...

---

## Detailed Notes

- **[10:32:15] Engineer A:** Drove rover around obstacle rock...
- **[10:45:00] Engineer B:** Arm extension test started...
```

**JSON output** groups notes into `summary`, `anomalies`, `detailed_notes` arrays.

---

### GET `/api/sessions/{sid}/notes/{note_id}` — Get Note

**Called by:** Frontend

---

### PUT `/api/sessions/{sid}/notes/{note_id}` — Edit Note (Replace)

**Called by:** Frontend (operator manually corrects AI-generated note)

**Request Body (all fields optional):**
```json
{
  "content": "Motor current rising to 2.5A (operator correction)",
  "speaker": "Engineer B",
  "type": "detail",
  "tags": ["motor", "current", "corrected"]
}
```

**Response `200`:** Updated note object.

**Side effect:** Broadcasts `note.updated` to all WebSocket clients.

---

### PATCH `/api/sessions/{sid}/notes/{note_id}` — Append to Note *(New in v0.3.0)*

**Called by: AI/Data Module** (when same anomaly recurs later in the session)

**Use case:** Operator notices motor vibration at 11:15. LLM creates anomaly note. At 14:30 same vibration recurs. LLM appends new observation to the existing note instead of creating a duplicate.

**Request Body:**
```json
{
  "append_content": "Vibration recurred during second arm extension test. Motor temp now at 85°C.",
  "timestamp": "2026-05-04T14:30:00Z",
  "telemetry_snapshot": {
    "motor_temp": 85.0
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `append_content` | string | ✅ | Text to append |
| `timestamp` | ISO datetime | ❌ | Defaults to now if omitted |
| `telemetry_snapshot` | object | ❌ | Merged into existing snapshot |

**What happens:** The `append_content` is added to the note's `content` on a new line with timestamp prefix:
```
Motor producing unusual vibration noise during arm extension.
[14:30:00] Vibration recurred during second arm extension test. Motor temp now at 85°C.
```

**Response `200`:** Updated note object with appended content.

**Side effect:** Broadcasts `note.appended` to all WebSocket clients.

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
  "timestamp": "2026-05-04T10:32:15Z",
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

**Called by: AI Module** (tool-call when LLM needs current telemetry)

**Example:**
```
GET /api/sessions/sess_abc/telemetry/latest?channel=battery_voltage
```

**Response `200`:** Single telemetry object with most recent value.

---

### GET `/api/sessions/{sid}/telemetry/channels` — List Channels

**Called by:** Frontend, AI Module

**Response `200`:**
```json
{ "channels": ["battery_voltage", "motor_current", "temperature"] }
```

---

## 4. STT Tasks API

Manages the lifecycle of speech-to-text audio chunks. Follows the **pause-based segmentation workflow**.

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
  "audio_chunk_id": "chunk_20260504_001",
  "duration_seconds": 8.4
}
```

**Response `201`:** STT task object with `status: "pending"`

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
| `note.created` | AI posts a new note | Full note object (check `type` field for routing) |
| `note.updated` | Operator edits a note | Updated note object |
| `note.appended` | AI appends to anomaly | Updated note object with appended content |
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
      // Route to correct UI section based on msg.data.type
      if (msg.data.type === "anomaly") addToAnomalyPanel(msg.data);
      else if (msg.data.type === "summary") showSummary(msg.data);
      else addToDetailedNotes(msg.data);
      break;
    case "note.updated":
      updateNoteInUI(msg.data);
      break;
    case "note.appended":
      // Same anomaly note, content has grown
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

---

## Quick Reference: Who Calls What

| Endpoint | Frontend | AI/Data Module |
|----------|----------|----------------|
| POST `/sessions` | ✅ | |
| GET/PATCH `/sessions` | ✅ | |
| POST `/notes` | | ✅ (with type) |
| GET `/notes` | ✅ | |
| GET `/notes?type=...` | ✅ | |
| GET `/notes/export` | ✅ | |
| PUT `/notes/{id}` (edit) | ✅ | |
| PATCH `/notes/{id}` (append) | | ✅ |
| DELETE `/notes/{id}` | ✅ | |
| POST `/telemetry` (ingest) | | ✅ |
| GET `/telemetry` (query) | ✅ | ✅ |
| GET `/telemetry/latest` | | ✅ |
| POST `/stt/tasks` | | ✅ |
| GET `/stt/tasks` | ✅ | |
| PUT `/stt/tasks/{tid}` | | ✅ |
| WS `/ws/sessions/{sid}` | ✅ (subscribe) | |
