# Frontend Integration Guide

**For:** Frontend Lead
**Backend version:** 0.2.0  
**Backend base URL:** `http://localhost:8000`  
**Last updated:** February 2025

---

## Overview

The backend is fully functional and ready to connect to. This guide walks you through everything you need to wire up the frontend.

**What the backend handles:**
- Session lifecycle management
- Storing and retrieving notes (created by AI module)
- Serving telemetry data
- Real-time push via WebSocket (note created/updated/deleted, STT task status)
- Export to Markdown / JSON

**What the frontend handles:**
- UI rendering
- Operator note editing (calls PUT `/notes/{id}`)
- WebSocket subscription for live updates
- Triggering export download
- Displaying STT task status / transcript chunks

---

## Step 1 — Start the Backend

```bash
cd astra-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI (interactive API docs): **http://localhost:8000/docs**

---

## Step 2 — Session Flow

### Create a session when the operator starts a test

```js
const response = await fetch("http://localhost:8000/api/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Motor Test Session #42",
    description: "Optional description"
  })
});
const session = await response.json();
const sessionId = session.id;  // e.g. "sess_a1b2c3d4"
```

Store `sessionId` — you'll pass it in every other API call.

### End a session when operator stops

```js
await fetch(`http://localhost:8000/api/sessions/${sessionId}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ status: "ended" })
});
```

---

## Step 3 — WebSocket (Real-Time Updates)

Connect as soon as a session is created. The backend will push events whenever the AI module creates/updates notes or finishes a transcription.

```js
const ws = new WebSocket(`ws://localhost:8000/ws/sessions/${sessionId}`);

ws.onopen = () => {
  console.log("Connected to ASTRA backend");
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  switch (msg.event) {
    case "note.created":
      // Add new note to the UI
      appendNote(msg.data);
      break;
    
    case "note.updated":
      // Update an existing note card
      updateNote(msg.data);
      break;
    
    case "note.deleted":
      // Remove note card
      removeNote(msg.data.id);
      break;
    
    case "stt.task.done":
      // Show transcript chunk (before it becomes a structured note)
      showTranscript(msg.data.transcript);
      break;
    
    case "error.occurred":
      // Show error banner
      showError(msg.data.message);
      break;
  }
};

// Keep connection alive
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send("ping");
  }
}, 30000);

// Disconnect cleanly when session ends
ws.close();
```

> **Note:** The backend session must exist before you connect the WebSocket. Create the session first (Step 2), then connect.

---

## Step 4 — Load Notes on Page Load

When a user opens an existing session, fetch the current notes to populate the UI:

```js
const response = await fetch(`http://localhost:8000/api/sessions/${sessionId}/notes`);
const notes = await response.json();
// notes is an array sorted by timestamp ascending
renderNotes(notes);
```

### Filtering notes (optional)

```js
// By speaker
fetch(`/api/sessions/${sessionId}/notes?speaker=Engineer A`)

// By type
fetch(`/api/sessions/${sessionId}/notes?type=observation`)

// By time range
fetch(`/api/sessions/${sessionId}/notes?from=2025-01-26T10:00:00Z&to=2025-01-26T11:00:00Z`)
```

---

## Step 5 — Operator Note Editing

When a user edits a note in the UI, call PUT. The backend will broadcast `note.updated` to all connected clients automatically.

```js
async function saveNoteEdit(sessionId, noteId, newContent) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/${sessionId}/notes/${noteId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: newContent
        // can also update: speaker, type, tags
      })
    }
  );
  const updatedNote = await response.json();
  return updatedNote;
}
```

---

## Step 6 — Export Notes

Wire this up to your export/download button:

```js
// Export as Markdown
async function exportMarkdown(sessionId) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/${sessionId}/notes/export?format=markdown`
  );
  const text = await response.text();
  
  // Trigger download
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `session_${sessionId}_notes.md`;
  a.click();
}

// Export as JSON
async function exportJSON(sessionId) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/${sessionId}/notes/export?format=json`
  );
  const text = await response.text();
  
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `session_${sessionId}_notes.json`;
  a.click();
}
```

---

## Step 7 — Telemetry Channels (Optional)

To show available telemetry channels in the UI:

```js
const response = await fetch(
  `http://localhost:8000/api/sessions/${sessionId}/telemetry/channels`
);
const { channels } = await response.json();
// channels: ["battery_voltage", "motor_current", "temperature"]
```

To query historical telemetry for a chart:

```js
const response = await fetch(
  `http://localhost:8000/api/sessions/${sessionId}/telemetry?channel=battery_voltage&limit=100`
);
const data = await response.json();
// sorted newest-first, each item has: timestamp, channel, value, unit
```

---

## Step 8 — STT Task Status (Optional)

You can show a processing indicator while Whisper is working. The WebSocket will push `stt.task.done` or `error.occurred` when it finishes — you don't need to poll.

But if you want to list all past chunks:

```js
const response = await fetch(
  `http://localhost:8000/api/sessions/${sessionId}/stt/tasks`
);
const tasks = await response.json();
// each task has: id, audio_chunk_id, status, transcript, duration_seconds
```

Task statuses: `pending` → `done` / `failed`

---

## Note Object Reference

```js
{
  id: "note_a1b2c3d4",
  session_id: "sess_xyz",
  timestamp: "2025-01-26T10:32:15Z",  // when observation was made
  speaker: "Engineer A",               // may be null
  content: "Motor current rising",
  type: "observation",                 // "observation" | "command" | "system"
  tags: ["motor", "current"],
  telemetry_snapshot: {                // may be null
    "battery_voltage": 32.5,
    "motor_current": 2.3
  },
  created_at: "2025-01-26T10:32:16Z",
  updated_at: "2025-01-26T10:32:16Z"
}
```

---

## CORS

The backend already has CORS enabled for:
- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

If you're running on a different port, let me know and I'll add it.

---

## Test the WebSocket Without the Frontend

Open `websocket_test.html` in a browser to verify real-time events are working before you integrate:

```bash
open websocket_test.html
```

Enter a session ID and click Connect. Then create a note via Swagger UI or curl to see it broadcast in real time.

---

## Common Errors

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `404 Session not found` | Wrong session ID | Check `sessionId` variable |
| `422 Unprocessable Entity` | Wrong request body format | Check field names/types against API contract |
| WebSocket closes immediately | Session doesn't exist yet | Create session before connecting WS |
| CORS error | Frontend port not in allow list | Tell Yulo to add your port |

---
