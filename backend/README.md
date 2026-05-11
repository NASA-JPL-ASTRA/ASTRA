# ASTRA Backend

FastAPI service that owns sessions, notes, telemetry, WebSocket broadcasting,
and OpenAI-based speech-to-text upload handling.


> Full API reference: [`docs/api-contract.md`](./docs/api-contract.md)

## Recording Path

```
frontend
  └─ POST /api/sessions/{sid}/stt/upload
       └─ OpenAI STT
            ├─ broadcast: transcript.chunk.ready  (live deltas)
            ├─ broadcast: stt.task.done           (final transcript)
            └─ create note + broadcast: note.created
```

The legacy local `whisper/` service has been removed.

## Quick Start

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then fill in OPENAI_API_KEY
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

**Why `--reload-dir app`:** On Windows (especially with OneDrive), files under `venv/` can be
touched by indexing or antivirus. The default `--reload` watches the whole working tree, so
WatchFiles may see thousands of `venv\Lib\site-packages\...` changes and **reload in a tight loop**,
which looks like “many errors” (`KeyboardInterrupt` / `CancelledError` during shutdown). Limiting
the watch to `app/` avoids that.

Use the same virtualenv for `uvicorn` as for `pip install` (e.g. `source venv/bin/activate` before
running the command, or `venv/bin/uvicorn app.main:app --reload --reload-dir app`). If you see
`ModuleNotFoundError: No module named 'influxdb_client'`, the optional telemetry query
dependencies were not installed in **that** interpreter — run `pip install -r requirements.txt`
again inside the activated venv.

Swagger UI: <http://localhost:8000/docs>  
Health:     <http://localhost:8000/health>

`load_dotenv()` runs at startup (see `app/main.py`), so `backend/.env` is picked
up automatically without exporting variables in your shell.

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENAI_API_KEY`             | ✅ | —                              | OpenAI key |
| `OPENAI_API_BASE_URL`        |    | `https://api.openai.com/v1`    | Override for proxy / Azure |
| `OPENAI_STT_MODEL`           |    | `gpt-4o-mini-transcribe`       | `gpt-4o-mini-transcribe` \| `gpt-4o-transcribe` \| `gpt-4o-transcribe-diarize` |
| `OPENAI_STT_LANGUAGE`        |    | `en`                           | ISO-639-1; project default English. Set empty in `.env` only if you need auto-detect. |
| `OPENAI_STT_PROMPT`          |    | —                              | Priming prompt for jargon / names |
| `OPENAI_STT_TIMEOUT_SECONDS` |    | `120`                          | HTTP timeout for OpenAI calls |

## Endpoints (summary)

```
Sessions   POST   /api/sessions
           GET    /api/sessions
           GET    /api/sessions/{sid}
           PATCH  /api/sessions/{sid}

Notes      POST   /api/sessions/{sid}/notes
           GET    /api/sessions/{sid}/notes
           GET    /api/sessions/{sid}/notes/export
           PUT    /api/sessions/{sid}/notes/{note_id}
           DELETE /api/sessions/{sid}/notes/{note_id}

Telemetry  POST   /api/sessions/{sid}/telemetry
           POST   /api/sessions/{sid}/telemetry/batch
           GET    /api/sessions/{sid}/telemetry
           GET    /api/sessions/{sid}/telemetry/latest?channel=
           GET    /api/sessions/{sid}/telemetry/channels

STT        POST   /api/sessions/{sid}/stt/upload
           POST   /api/sessions/{sid}/stt/tasks
           GET    /api/sessions/{sid}/stt/tasks
           GET    /api/sessions/{sid}/stt/tasks/{tid}
           PUT    /api/sessions/{sid}/stt/tasks/{tid}

WebSocket  WS     /ws/sessions/{sid}
```

Each session response includes `note_count`, computed from stored notes.

## Project Layout

```
app/
├── main.py                  FastAPI app + load_dotenv() + router registration
├── database.py              In-memory storage helpers
├── ws_manager.py            Session event broadcasting
├── routes/
│   ├── sessions.py          Session CRUD + note_count
│   ├── notes.py             Note CRUD + export
│   ├── telemetry.py         Telemetry ingest + queries
│   ├── stt.py               Audio upload + OpenAI STT integration
│   └── websocket.py         /ws/sessions/{sid}
├── services/
│   └── openai_stt.py        OpenAI streaming transcription client
└── schemas/                 Pydantic request/response models
```

## Verification

```bash
python -m compileall app
python smoke_test.py
```

