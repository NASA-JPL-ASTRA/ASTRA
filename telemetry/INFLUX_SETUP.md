# InfluxDB Telemetry Setup

This project uses InfluxDB 2.x for telemetry query testing. Do not commit a local
InfluxDB container image or data volume; recreate the database from the checked-in
Compose service and telemetry logs.

## 1. Start InfluxDB

Make sure `backend/.env` exists because `docker-compose.yml` references it:

```bash
cp backend/.env.example backend/.env
```

From the repository root:

```bash
docker compose up -d influxdb
```

The local defaults match `backend/.env.example`:

```env
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=aistra-dev-token-12345
INFLUX_ORG=aistra-org
INFLUX_BUCKET=telemetry
```

When the backend runs inside Docker Compose, it uses `http://influxdb:8086`
through the Compose service network.

## 2. Generate Telemetry Logs

The repository includes generated test logs under
`telemetry/telemetry-generator/output`. If they are missing or you want to
regenerate them:

```bash
cd telemetry/telemetry-generator
python generate_all.py
```

## 3. Ingest All Test Scenarios

Install the InfluxDB Python client if your environment does not already have it:

```bash
python -m pip install -r telemetry/requirements.txt
```

From the repository root:

```bash
./telemetry/ingest_all.sh
```

This ingests:

- `test_1_straight_line`
- `test_2_uphill`
- `test_3_stops_starts_turns`
- `test_4_motor_stall`
- `test_5_imu_malfunction`
- `test_6_command_error`

Each scenario name is written as the InfluxDB `session_id` tag. Voice telemetry
queries use that tag, so the scenario names in the UI must match these values.

## 4. Run Backend And Frontend

Backend:

```bash
cd backend
cp .env.example .env
./venv/bin/python -m uvicorn app.main:app --reload --reload-dir app
```

Frontend:

```bash
cd frontend
npm run dev
```

## Useful Checks

Confirm InfluxDB is running:

```bash
curl http://localhost:8086/health
```

Confirm the backend can query telemetry:

```bash
curl "http://localhost:8000/api/query/events?session=test_4_motor_stall&t0=0&t1=4102444800&limit=5"
```

## Reset Local InfluxDB Data

This deletes the local InfluxDB volume and all ingested telemetry:

```bash
docker compose down -v
docker compose up -d influxdb
./telemetry/ingest_all.sh
```
