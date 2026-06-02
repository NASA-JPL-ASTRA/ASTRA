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

Clone and switch to the confidence branch:

```bash
git clone git@github.com:NASA-JPL-ASTRA/ASTRA.git
cd ASTRA
git checkout confidence
git pull origin confidence
```

Start the backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and set at least:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
OPENAI_STT_LANGUAGE=en
STT_ENGLISH_ONLY_GATE=true
```

For confidence scores, use `gpt-4o-mini-transcribe` or `gpt-4o-transcribe`.
Avoid `gpt-4o-transcribe-diarize` for demos because it does not expose the same
token log-probabilities used by the confidence scorer.

Run the backend with the virtualenv Python:

```bash
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal from the repository root:

```bash
cd /path/to/ASTRA/frontend
npm install
cp .env.example .env.local
npm run dev
```

Backend Swagger UI: <http://localhost:8000/docs>  
Frontend dev UI:    <http://localhost:5173>

If confidence scores show as `0%`, verify:

```bash
git branch --show-current
git log --oneline -3
```

The branch must be `confidence`, the latest commits should include
`Restore STT confidence filtering`, and the backend must be restarted after
editing `backend/.env`.

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

