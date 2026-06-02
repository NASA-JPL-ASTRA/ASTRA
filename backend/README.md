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
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

cp .env.example .env          # then fill in OPENAI_API_KEY
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
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

### Anaconda / Conda Python

If your terminal prompt shows `(base)` and `python3 -m venv venv` fails with
`ensurepip` errors or `pip` segmentation faults, your conda Python is not
creating a healthy standard `venv`. Remove the broken `venv` and use a dedicated
conda environment:

```bash
cd /Users/haochenzhao/Desktop/ASTRA-dev/backend
deactivate 2>/dev/null || true
rm -rf venv

conda create -n astra python=3.11 -y
conda activate astra
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cp -n .env.example .env
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

For later backend runs:

```bash
cd /Users/haochenzhao/Desktop/ASTRA-dev/backend
conda activate astra
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

Swagger UI: <http://localhost:8000/docs>  
Health:     <http://localhost:8000/health>

`load_dotenv()` runs at startup (see `app/main.py`), so `backend/.env` is picked
up automatically without exporting variables in your shell.

## Confidence Scores and Notes

The `confidence` branch computes a `confidence` value for each completed STT
task. For `gpt-4o-mini-transcribe` and `gpt-4o-transcribe`, the backend asks
OpenAI for token log probabilities and derives model confidence from them. If
log probabilities are unavailable, the backend falls back to an audio/text signal
estimate.

Successful confidence calculation prints a backend log line like:

```text
STT confidence task=... model=... value=... source=... logprob_count=...
```

If another developer sees every transcript as `0%` in the frontend, they should
confirm they are running the latest `confidence` branch and have restarted the
backend after pulling:

```bash
git branch --show-current
git log --oneline -3
```

Saved notes are intentionally stricter than live transcripts. A transcript is
shown in the live panel after STT finishes, but it is saved into notes only when
its confidence is at least `65%` and it passes the text-quality filters. This
keeps low-confidence speech and common background-noise hallucinations out of the
canonical notes.

## Background Noise / Hallucination Tips

Speech-to-text can hallucinate words from fans, keyboard noise, music, or people
talking in the background. The frontend already drops very quiet chunks and short
bursts before upload, and the browser requests noise suppression and echo
cancellation. For best results:

- Use a headset or directional microphone when possible.
- Keep the mic away from keyboards, speakers, and fans.
- Speak in short phrases with small pauses; pauses help ASTRA split chunks.
- Treat low-confidence live text as review-only; it will not be saved as a note
  below the `65%` threshold.

## Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `OPENAI_API_KEY`             | ✅ | —                              | OpenAI key |
| `OPENAI_API_BASE_URL`        |    | `https://api.openai.com/v1`    | Override for proxy / Azure |
| `OPENAI_STT_MODEL`           |    | `gpt-4o-mini-transcribe`       | `gpt-4o-mini-transcribe` \| `gpt-4o-transcribe` \| `gpt-4o-transcribe-diarize` |
| `OPENAI_STT_LANGUAGE`        |    | `en`                           | ISO-639-1; project default English. Set empty in `.env` only if you need auto-detect. |
| `OPENAI_STT_PROMPT`          |    | *(empty)*                      | Optional vocabulary hints only (not instructions); empty avoids prompt leaking into streamed text |
| `OPENAI_STT_TIMEOUT_SECONDS` |    | `120`                          | HTTP timeout for OpenAI calls |
| `STT_ENGLISH_ONLY_GATE`      |    | `true`                         | If true, non-English transcripts are discarded (not broadcast to UI) |

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

