"""
AiSTRA telemetry query helpers — InfluxDB (Flux).

Lifted from telemetry/query.py; connection settings come from environment variables.
Settings are read at query time (not only at import) so they always match ``backend/.env``
after ``load_dotenv`` in ``app.main`` (and so cwd does not matter).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient

_DEFAULT_LOOKBACK = 30 * 24 * 3600


@dataclass(frozen=True, slots=True)
class _InfluxSettings:
    url: str
    token: str
    org: str
    bucket: str
    timeout_ms: int
    lookback_s: float


def _influx_settings() -> _InfluxSettings:
    url = os.getenv("INFLUX_URL", "http://localhost:8086").strip()
    token = os.getenv("INFLUX_TOKEN", "aistra-dev-token-12345").strip()
    org = os.getenv("INFLUX_ORG", "aistra-org").strip()
    bucket = os.getenv("INFLUX_BUCKET", "telemetry").strip()
    raw_timeout = os.getenv("INFLUX_TIMEOUT_MS", "30000")
    try:
        timeout_ms = int(raw_timeout)
    except (TypeError, ValueError):
        timeout_ms = 30_000
    timeout_ms = max(1000, timeout_ms)

    raw_lb = os.getenv("INFLUX_POINT_LOOKBACK_SECONDS", str(_DEFAULT_LOOKBACK))
    try:
        lookback_s = float(raw_lb)
    except (TypeError, ValueError):
        lookback_s = float(_DEFAULT_LOOKBACK)
    # ``at - lookback`` must be strictly below ``at`` or Flux ``range`` can be empty (e.g. lookback 0).
    lookback_s = max(60.0, lookback_s)

    return _InfluxSettings(
        url=url or "http://localhost:8086",
        token=token or "aistra-dev-token-12345",
        org=org or "aistra-org",
        bucket=bucket or "telemetry",
        timeout_ms=timeout_ms,
        lookback_s=lookback_s,
    )


def _ts(unix_seconds: float) -> str:
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _flux_time(unix_seconds: float) -> str:
    return f'time(v: "{_ts(unix_seconds)}")'


def _client() -> InfluxDBClient:
    s = _influx_settings()
    return InfluxDBClient(
        url=s.url,
        token=s.token,
        org=s.org,
        timeout=s.timeout_ms,
    )


def get_channel_value(
    session_id: str, channel: str, at_time: float
) -> dict | None:
    s = _influx_settings()
    stop = _flux_time(at_time)
    start_unix = max(0.0, at_time - s.lookback_s)
    start = _flux_time(start_unix)

    query = f"""
    from(bucket: "{s.bucket}")
      |> range(start: {start}, stop: {stop})
      |> filter(fn: (r) => r._measurement == "telemetry_channel")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r.channel == "{channel}")
      |> last()
    """

    with _client() as client:
        tables = client.query_api().query(query, org=s.org)
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

    s = _influx_settings()
    start = _flux_time(start_time)
    end = _flux_time(end_time)

    query = f"""
    data = from(bucket: "{s.bucket}")
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
        tables = client.query_api().query(query, org=s.org)
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

    s = _influx_settings()
    start = _flux_time(start_time)
    end = _flux_time(end_time)

    severity_filter = ""
    if severity != "all":
        severity_filter = f'|> filter(fn: (r) => r.severity == "{severity}")'

    query = f"""
    from(bucket: "{s.bucket}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_event")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r._field == "message")
      {severity_filter}
      |> limit(n: {limit})
    """

    events: list = []
    with _client() as client:
        tables = client.query_api().query(query, org=s.org)
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
