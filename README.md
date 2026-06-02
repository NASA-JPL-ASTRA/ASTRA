# ASTRA

Advanced System for Testbed Recording and Analysis. ASTRA records browser-based
testbed sessions, transcribes voice notes with OpenAI STT, and stores notes plus
telemetry for review and export.

## Architecture

```text
Frontend (React/Vite)
  -> POST audio chunks
Backend (FastAPI)
  -> OpenAI STT
  -> WebSocket live transcript / notes
  -> In-memory sessions + notes
  -> InfluxDB telemetry queries
```

- Backend: `backend/`
- Frontend: `frontend/`
- Telemetry setup: `telemetry/`

## Local Setup

### Backend

Use this for local development. `--reload` restarts the backend when files in
`backend/app/` change.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
```

Set at least `OPENAI_API_KEY` in `backend/.env`. For telemetry, also set:

```env
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=aistra-dev-token-12345
INFLUX_ORG=aistra-org
INFLUX_BUCKET=telemetry
```

Backend docs: <http://localhost:8000/docs>  
Health check: <http://localhost:8000/health>

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Default frontend env:

```env
VITE_API_URL=http://localhost:8000/api
VITE_SESSION_WS_URL=ws://localhost:8000/ws/sessions
```

Frontend: <http://localhost:5173>

## Production on EC2

### Backend

The EC2 backend runs with Docker Compose. Make sure Docker and Docker Compose
are installed on the instance, then create `backend/.env`:

```bash
cp backend/.env.example backend/.env
```

Set the backend secret in `backend/.env`:

```env
OPENAI_API_KEY=real_key
```

Set Docker Compose production values in a root `.env` file or in the shell:

```env
BACKEND_CORS_ORIGINS=https://your-domain.com
INFLUX_TOKEN=strong_production_token
INFLUX_ORG=your_org
INFLUX_BUCKET=telemetry
```

Start the backend and InfluxDB:

```bash
docker compose up -d --build backend
docker compose ps
curl http://localhost:8000/health
```

`docker-compose.yml` builds `backend/Dockerfile`, starts InfluxDB, and restarts
containers automatically with `restart: unless-stopped`.

### Frontend

Build the frontend with production API URLs. This project does not currently
serve the frontend through Docker, so serve `frontend/dist/` with Nginx or
another static file server:

```bash
cd frontend
npm install
cp .env.example .env.production
npm run build
```

Example `frontend/.env.production`:

```env
VITE_API_URL=https://your-domain.com/api
VITE_SESSION_WS_URL=wss://your-domain.com/ws/sessions
```

Typical EC2 setup:

- Nginx serves the frontend on `https://your-domain.com`
- Nginx proxies `/api` to `http://127.0.0.1:8000/api`
- Nginx proxies `/ws` to `http://127.0.0.1:8000/ws`
- The EC2 security group opens `80` and `443`, but not `8000`

## InfluxDB

```bash
docker compose up -d influxdb
curl http://localhost:8086/health

python -m pip install -r telemetry/requirements.txt
./telemetry/ingest_all.sh
```

Verify backend telemetry queries:

```bash
curl "http://localhost:8000/api/query/events?session=test_4_motor_stall&t0=0&t1=4102444800&limit=5"
```

## Documentation

| Topic | File |
|-------|------|
| Project overview | `README.md` |
| Backend setup | `backend/README.md` |
| Frontend setup | `frontend/README.md` |
| API contract | `backend/docs/api-contract.md` |
| InfluxDB setup | `telemetry/INFLUX_SETUP.md` |

## Environment Files

Real env files are git-ignored:

- `backend/.env`
- `frontend/.env.local`

Only templates should be committed:

- `backend/.env.example`
- `frontend/.env.example`
