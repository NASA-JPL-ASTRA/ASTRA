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

```bash
# 1) Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in OPENAI_API_KEY
# Use the venv’s Python so deps (e.g. influxdb_client) match pip — not a global `uvicorn` on PATH.
./venv/bin/python -m uvicorn app.main:app --reload

# 2) Frontend (in another terminal)
cd frontend
npm install
cp .env.example .env.local    # adjust URLs if backend is not on :8000
npm run dev
```

Backend Swagger UI: <http://localhost:8000/docs>  
Frontend dev UI:    <http://localhost:5173>

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

## Secrets & Environment

Two env files are needed locally (both are git-ignored):

- `backend/.env`        — copy from `backend/.env.example`, set `OPENAI_API_KEY`
- `frontend/.env.local` — copy from `frontend/.env.example`

Never commit real keys. See `backend/README.md` for the supported variables.


