"""
AiSTRA telemetry query helpers — InfluxDB (Flux).

Lifted from telemetry/query.py; connection settings come from environment variables.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "aistra-dev-token-12345")
INFLUX_ORG = os.getenv("INFLUX_ORG", "aistra-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")

# HTTP read/connect timeout for Influx (ms). Without this, a dead host can block forever.
INFLUX_TIMEOUT_MS = int(os.getenv("INFLUX_TIMEOUT_MS", "30000"))

# ``get_channel_value`` must not use range(start: 0) — that scans the full bucket and stalls.
# Only search this many seconds before ``at_time`` (default: 30 days).
INFLUX_POINT_LOOKBACK_SECONDS = int(
    os.getenv("INFLUX_POINT_LOOKBACK_SECONDS", str(30 * 24 * 3600))
)


def _ts(unix_seconds: float) -> str:
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _flux_time(unix_seconds: float) -> str:
    return f'time(v: "{_ts(unix_seconds)}")'


def _client() -> InfluxDBClient:
    return InfluxDBClient(
        url=INFLUX_URL,
        token=INFLUX_TOKEN,
        org=INFLUX_ORG,
        timeout=INFLUX_TIMEOUT_MS,
    )


def get_channel_value(
    session_id: str, channel: str, at_time: float
) -> dict | None:
    stop = _flux_time(at_time)
    start_unix = max(0.0, at_time - float(INFLUX_POINT_LOOKBACK_SECONDS))
    start = _flux_time(start_unix)

    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "telemetry_channel")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r.channel == "{channel}")
      |> last()
    """

    with _client() as client:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        for table in tables:
            for record in table.records:
                return {
                    "channel": channel,
                    "value": record.get_value(),
                    "timestamp": record.get_time().timestamp(),
                }
    return None


def query_channel_range(
    session_id: str,
    channel: str,
    start_time: float,
    end_time: float,
) -> dict | None:
    if end_time <= start_time:
        return None

    start = _flux_time(start_time)
    end = _flux_time(end_time)

    query = f"""
    data = from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_channel")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r.channel == "{channel}")

    min_val  = data |> min()  |> map(fn: (r) => ({{r with stat: "min"}}))
    max_val  = data |> max()  |> map(fn: (r) => ({{r with stat: "max"}}))
    mean_val = data |> mean() |> map(fn: (r) => ({{r with stat: "mean"}}))
    last_val = data |> last() |> map(fn: (r) => ({{r with stat: "last"}}))

    union(tables: [min_val, max_val, mean_val, last_val])
    """

    result: dict = {
        "channel": channel,
        "session_id": session_id,
        "start": start_time,
        "end": end_time,
    }

    with _client() as client:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        for table in tables:
            for record in table.records:
                stat = record.values.get("stat")
                if stat:
                    result[stat] = record.get_value()

    return result if "min" in result else None


def get_recent_events(
    session_id: str,
    start_time: float,
    end_time: float,
    severity: str = "all",
    limit: int = 20,
) -> list:
    if end_time <= start_time:
        return []

    start = _flux_time(start_time)
    end = _flux_time(end_time)

    severity_filter = ""
    if severity != "all":
        severity_filter = f'|> filter(fn: (r) => r.severity == "{severity}")'

    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_event")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r._field == "message")
      {severity_filter}
      |> limit(n: {limit})
    """

    events: list = []
    with _client() as client:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        for table in tables:
            for record in table.records:
                events.append(
                    {
                        "timestamp": record.get_time().timestamp(),
                        "evr_name": record.values.get("evr_name"),
                        "severity": record.values.get("severity"),
                        "message": record.get_value(),
                    }
                )

    return sorted(events, key=lambda e: e["timestamp"])
