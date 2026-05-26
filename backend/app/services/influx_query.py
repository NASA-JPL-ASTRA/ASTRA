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
_DEFAULT_QUERY_START = 0.0
_DEFAULT_QUERY_END = 4102444800.0  # 2100-01-01T00:00:00Z


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
    dt = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


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


def _default_query_window() -> tuple[float, float]:
    raw_start = os.getenv("INFLUX_QUERY_START_SECONDS", str(_DEFAULT_QUERY_START))
    raw_end = os.getenv("INFLUX_QUERY_END_SECONDS", str(_DEFAULT_QUERY_END))
    try:
        start = float(raw_start)
    except (TypeError, ValueError):
        start = _DEFAULT_QUERY_START
    try:
        end = float(raw_end)
    except (TypeError, ValueError):
        end = _DEFAULT_QUERY_END
    if start >= end:
        return _DEFAULT_QUERY_START, _DEFAULT_QUERY_END
    return max(0.0, start), end


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


def get_session_events(
    session_id: str,
    start_time: float | None = None,
    end_time: float | None = None,
    severity: str = "all",
    limit: int | None = None,
) -> list:
    start_default, end_default = _default_query_window()
    start_time = start_default if start_time is None else start_time
    end_time = end_default if end_time is None else end_time
    if end_time <= start_time:
        return []

    s = _influx_settings()
    start = _flux_time(start_time)
    end = _flux_time(end_time)
    max_rows = limit
    if max_rows is None:
        raw_limit = os.getenv("INFLUX_EVENT_QUERY_LIMIT", "5000")
        try:
            max_rows = int(raw_limit)
        except (TypeError, ValueError):
            max_rows = 5000
    max_rows = max(1, min(50_000, int(max_rows)))

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
      |> limit(n: {max_rows})
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


def get_channel_samples(
    session_id: str,
    channel: str,
    start_time: float | None = None,
    end_time: float | None = None,
    limit: int = 10,
) -> list:
    start_default, end_default = _default_query_window()
    start_time = start_default if start_time is None else start_time
    end_time = end_default if end_time is None else end_time
    if end_time <= start_time:
        return []

    s = _influx_settings()
    start = _flux_time(start_time)
    end = _flux_time(end_time)
    limit = max(1, min(50_000, int(limit)))

    query = f"""
    from(bucket: "{s.bucket}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_channel")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r.channel == "{channel}")
      |> limit(n: {limit})
    """

    samples: list = []
    with _client() as client:
        tables = client.query_api().query(query, org=s.org)
        for table in tables:
            for record in table.records:
                samples.append(
                    {
                        "timestamp": record.get_time().timestamp(),
                        "value": record.get_value(),
                    }
                )
    return sorted(samples, key=lambda item: item["timestamp"])


def count_channel_samples(
    session_id: str,
    channel: str,
    start_time: float | None = None,
    end_time: float | None = None,
) -> int:
    start_default, end_default = _default_query_window()
    start_time = start_default if start_time is None else start_time
    end_time = end_default if end_time is None else end_time
    if end_time <= start_time:
        return 0

    s = _influx_settings()
    start = _flux_time(start_time)
    end = _flux_time(end_time)

    query = f"""
    from(bucket: "{s.bucket}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_channel")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r.channel == "{channel}")
      |> count()
    """

    total = 0
    with _client() as client:
        tables = client.query_api().query(query, org=s.org)
        for table in tables:
            for record in table.records:
                try:
                    total += int(record.get_value())
                except (TypeError, ValueError):
                    continue
    return total


def query_channel_range_default(session_id: str, channel: str) -> dict | None:
    start, end = _default_query_window()
    return query_channel_range(
        session_id=session_id,
        channel=channel,
        start_time=start,
        end_time=end,
    )
