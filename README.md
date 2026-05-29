# ASTRA — Advanced System for Testbed Recording and Analysis

> UW ENGINE Capstone Project, sponsored by NASA JPL. Records testbed sessions in the browser, transcribes
> voice notes through OpenAI STT, and stores structured notes & telemetry that
> can be exported to Markdown / JSON.
>


## Architecture

```
┌──────────────┐   audio chunks    ┌────────────┐   transcribe    ┌────────┐
│  Frontend    │ ────────────────▶ │  Backend   │ ──────────────▶ │ OpenAI │
│  (React/Vite)│                   │ (FastAPI)  │ ◀────────────── │  STT   │
│              │ ◀──── WS ─────── │            │                  └────────┘
└──────────────┘  note.created     └────────────┘
                  stt.task.done           │
                                           ▼
                                     in-memory DB
                                  (sessions / notes /
                                   telemetry / stt_tasks)
```

- **Backend**: FastAPI service. Owns sessions, notes, telemetry, WebSocket
  broadcasting, and OpenAI-based speech-to-text. Storage is in-memory today
  (Postgres is on the roadmap).
- **Frontend**: React + TypeScript + Vite. Captures microphone audio, uploads
  chunks to the backend, and renders live transcripts / notes via WebSocket.

## Quick Start

Clone or update the branch that contains transcript confidence support:

```bash
git clone git@github.com:NASA-JPL-ASTRA/ASTRA.git
cd ASTRA
git checkout confidence
git pull origin confidence
git log --oneline -3
```

The latest commits on this branch should include confidence-related changes such
as `Lower auto note confidence threshold` and `Remove manual note confirmation`.
If normal SSH to GitHub hangs, pull over SSH port 443 instead:

```bash
git pull ssh://git@ssh.github.com:443/NASA-JPL-ASTRA/ASTRA.git confidence
```

```bash
# 1) Backend
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cp .env.example .env          # then fill in OPENAI_API_KEY
# Use the venv’s Python so deps (e.g. influxdb_client) match pip — not a global `uvicorn` on PATH.
./venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000

# 2) Frontend (in another terminal)
cd frontend
npm install
cp .env.example .env.local    # adjust URLs if backend is not on :8000
npm run dev
```

Backend Swagger UI: <http://localhost:8000/docs>  
Frontend dev UI:    <http://localhost:5173>

## Confidence Score Checklist

If confidence scores show as `0%` on another machine, check these first:

```bash
git branch --show-current
git log --oneline -3
```

The branch must be `confidence`, and the latest commits must include the
confidence-score commits. After pulling, restart both backend and frontend; a
browser refresh alone is not enough if the old backend process is still running.

The backend logs one line per completed STT task when confidence is calculated:

```text
STT confidence task=... value=... source=... logprob_count=...
```

If this line never appears, the backend is not running the confidence branch, or
the audio never reached the STT route. If the line appears but the frontend still
shows `0%`, check `frontend/.env.local` and make sure `VITE_API_URL` and
`VITE_SESSION_WS_URL` point to the backend you just restarted.

Notes are created only when the transcript passes text-quality filters and has
confidence at least `65%`. Lower-confidence transcripts may still appear in the
live transcript panel, but they are not saved as notes.

## Reducing STT Hallucinations

Background noise can be transcribed as fake speech by any speech-to-text model.
ASTRA reduces this in three places:

- The browser enables echo cancellation and noise suppression before upload.
- Very quiet chunks and very short bursts are dropped before they reach OpenAI.
- The backend does not save transcripts below `65%` confidence into notes.

For demos, use a headset or directional microphone, keep the room quiet, and
pause briefly between phrases. If hallucinations still appear in the live panel,
check whether the confidence is low; low-confidence text is expected to be
visible for operator review but excluded from saved notes.

## Repository Layout

```
ATSRA/
├── backend/                 FastAPI service
│   ├── app/                 Routes, services, in-memory DB
│   ├── docs/api-contract.md REST + WebSocket reference
│   └── README.md
├── frontend/                React + Vite client
│   └── README.md
└── README.md                (this file)
```

## Documentation

| Topic | English | 中文 |
|-------|---------|------|
| Project overview | `README.md` | `README.zh.md` |
| Backend setup    | `backend/README.md`  | `backend/README.zh.md` |
| Frontend setup   | `frontend/README.md` | `frontend/README.zh.md` |
| API contract (REST + WS) | `backend/docs/api-contract.md` | `backend/docs/api-contract.zh.md` |
| InfluxDB telemetry setup | `telemetry/INFLUX_SETUP.md` | — |

## Secrets & Environment

Two env files are needed locally (both are git-ignored):

- `backend/.env`        — copy from `backend/.env.example`, set `OPENAI_API_KEY`
- `frontend/.env.local` — copy from `frontend/.env.example`

Never commit real keys. See `backend/README.md` for the supported variables.

