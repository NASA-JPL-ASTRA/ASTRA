"""
AiSTRA Telemetry Query Helpers

Three functions that read telemetry back out of InfluxDB.
These become the Flask API backend.

All time arguments are Unix timestamps (float, seconds).
All functions accept a session_id so queries are always session-scoped.
"""

from datetime import datetime, timezone
from influxdb_client import InfluxDBClient

# ── Connection config — must match your docker run command ────────────────────
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "aistra-dev-token-12345"
INFLUX_ORG    = "aistra-org"
INFLUX_BUCKET = "telemetry"
INFLUX_TIMEOUT_MS = 30_000
# Do not use range(start: 0) — it scans the whole bucket. Default 30d lookback before ``at_time``.
POINT_LOOKBACK_SEC = 30 * 24 * 3600


def _ts(unix_seconds: float) -> str:
    """Convert a Unix timestamp (seconds) to RFC3339 string for Flux queries."""
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _flux_time(unix_seconds: float) -> str:
    """Return a Flux time literal from Unix seconds."""
    return f'time(v: "{_ts(unix_seconds)}")'


def _client():
    """Return a new InfluxDB client. Used as a context manager so connections close cleanly."""
    return InfluxDBClient(
        url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=INFLUX_TIMEOUT_MS
    )


# ─────────────────────────────────────────────────────────────────────────────
# Function 1: get_channel_value
# ─────────────────────────────────────────────────────────────────────────────

def get_channel_value(session_id: str, channel: str, at_time: float) -> dict | None:
    """
    Return the most recent value of a channel at or before `at_time`.

    Args:
        session_id  e.g. "test_4_motor_stall"
        channel     e.g. "motors.motor4_current"
        at_time     Unix timestamp (seconds) — the moment of interest

    Returns:
        {"channel": str, "value": float, "timestamp": float}
        or None if no data exists before at_time for this channel/session.

    Flux query explanation:
        Bounded range ending at at_time (not from epoch) — full-bucket scans hang Influx.
        last() — most recent point in that window.
    """
    stop = _flux_time(at_time)
    start_unix = max(0.0, at_time - float(POINT_LOOKBACK_SEC))
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
                    "channel":   channel,
                    "value":     record.get_value(),
                    "timestamp": record.get_time().timestamp(),
                }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Function 2: query_channel_range
# ─────────────────────────────────────────────────────────────────────────────

def query_channel_range(session_id: str, channel: str,
                        start_time: float, end_time: float) -> dict | None:
    """
    Return min, max, mean, and last value of a channel over a time window.

    Args:
        session_id   e.g. "test_4_motor_stall"
        channel      e.g. "motors.motor4_current"
        start_time   Unix timestamp (seconds) — window start
        end_time     Unix timestamp (seconds) — window end

    Returns:
        {
          "channel":    str,
          "session_id": str,
          "start":      float,
          "end":        float,
          "min":        float,
          "max":        float,
          "mean":       float,
          "last":       float,
        }
        or None if no data exists in the window.

    Flux query explanation:
        We run four separate aggregations on the same filtered data
        (min, max, mean, last), tag each result with a "stat" column,
        then union them into one table so we can read all four in one
        network round-trip instead of four separate queries.
    """
    if end_time <= start_time:
        return None

    start = _flux_time(start_time)
    end   = _flux_time(end_time)

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

    result = {
        "channel":    channel,
        "session_id": session_id,
        "start":      start_time,
        "end":        end_time,
    }

    with _client() as client:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        for table in tables:
            for record in table.records:
                stat = record.values.get("stat")
                if stat:
                    result[stat] = record.get_value()

    # Return None if we got no stats back (no data in window)
    return result if "min" in result else None


# ─────────────────────────────────────────────────────────────────────────────
# Function 3: get_recent_events
# ─────────────────────────────────────────────────────────────────────────────

def get_recent_events(session_id: str, start_time: float, end_time: float,
                      severity: str = "all", limit: int = 20) -> list:
    """
    Return EVR events within a time window, sorted by timestamp ascending.

    Args:
        session_id   e.g. "test_4_motor_stall"
        start_time   Unix timestamp (seconds)
        end_time     Unix timestamp (seconds)
        severity     "all" | "warning" | "activity_hi" | "activity_lo" | "command"
        limit        max number of events to return (default 20)

    Returns:
        List of dicts, each:
        {"timestamp": float, "evr_name": str, "severity": str, "message": str}
        Empty list if no events match.

    Note on the InfluxDB UI error you saw ("unsupported input type for mean aggregate: string"):
        That error appears in the UI because the UI tries to apply mean() to the
        "message" field which is a string. This function avoids that by never
        calling mean() on event data — we just fetch raw records directly.
    """
    if end_time <= start_time:
        return []

    start = _flux_time(start_time)
    end   = _flux_time(end_time)

    # Only add the severity filter line if a specific severity was requested
    severity_filter = ""
    if severity != "all":
        severity_filter = f'|> filter(fn: (r) => r.severity == "{severity}")'

    # We filter to _field == "message" so we get one row per event
    # (InfluxDB stores both "value" placeholder and "message" as separate fields;
    #  "message" is the one that contains the human-readable text)
    query = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {start}, stop: {end})
      |> filter(fn: (r) => r._measurement == "telemetry_event")
      |> filter(fn: (r) => r.session_id == "{session_id}")
      |> filter(fn: (r) => r._field == "message")
      {severity_filter}
      |> limit(n: {limit})
    """

    events = []
    with _client() as client:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        for table in tables:
            for record in table.records:
                events.append({
                    "timestamp": record.get_time().timestamp(),
                    "evr_name":  record.values.get("evr_name"),
                    "severity":  record.values.get("severity"),
                    "message":   record.get_value(),
                })

    return sorted(events, key=lambda e: e["timestamp"])