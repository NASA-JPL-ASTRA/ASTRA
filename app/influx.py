"""
InfluxDB Connection

Connects to Yuyang's InfluxDB Docker instance for telemetry reads.
Connection defaults match his ingestor.py setup.

Override via environment variables:
    INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
"""

import os
from datetime import datetime, timezone

INFLUX_URL    = os.getenv("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN",  "aistra-dev-token-12345")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "aistra-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")

# Measurement names (must match Yuyang's ingestor.py)
MEAS_CHANNEL = "telemetry_channel"
MEAS_EVENT   = "telemetry_event"

_client = None
_query_api = None


def get_query_api():
    """Lazy-init InfluxDB client. Returns None if influxdb-client not installed."""
    global _client, _query_api
    if _query_api is not None:
        return _query_api
    try:
        from influxdb_client import InfluxDBClient
        _client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        _query_api = _client.query_api()
        return _query_api
    except ImportError:
        return None
    except Exception:
        return None


def flux_query(flux: str) -> list:
    """Run a Flux query and return list of dicts. Returns [] if InfluxDB unavailable."""
    api = get_query_api()
    if api is None:
        return []
    try:
        tables = api.query(flux, org=INFLUX_ORG)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results
    except Exception:
        return []


def get_channels(session_id: str) -> list:
    """List all channel names for a session."""
    flux = f'''
    import "influxdata/influxdb/schema"
    schema.tagValues(
        bucket: "{INFLUX_BUCKET}",
        tag: "channel",
        predicate: (r) => r._measurement == "{MEAS_CHANNEL}"
            and r.session_id == "{session_id}"
    )
    '''
    rows = flux_query(flux)
    return sorted([r["_value"] for r in rows])


def get_latest(session_id: str, channel: str) -> dict | None:
    """Get latest value for a channel."""
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
        |> range(start: 0)
        |> filter(fn: (r) => r._measurement == "{MEAS_CHANNEL}")
        |> filter(fn: (r) => r.session_id == "{session_id}")
        |> filter(fn: (r) => r.channel == "{channel}")
        |> filter(fn: (r) => r._field == "value")
        |> last()
    '''
    rows = flux_query(flux)
    if not rows:
        return None
    r = rows[0]
    return {
        "id":         "tel_influx",
        "session_id": session_id,
        "timestamp":  r.get("_time", datetime.now(timezone.utc)),
        "channel":    channel,
        "value":      r.get("_value", 0.0),
        "unit":       None,
    }


def query_range(
    session_id: str,
    channel: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int = 1000,
) -> list:
    """Query telemetry with optional filters."""
    start = "0"
    if from_time:
        start = from_time.isoformat().replace("+00:00", "Z")
    stop = "now()"
    if to_time:
        stop = to_time.isoformat().replace("+00:00", "Z")

    ch_filter = ""
    if channel:
        ch_filter = f'|> filter(fn: (r) => r.channel == "{channel}")'

    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {start}, stop: {stop})
        |> filter(fn: (r) => r._measurement == "{MEAS_CHANNEL}")
        |> filter(fn: (r) => r.session_id == "{session_id}")
        {ch_filter}
        |> filter(fn: (r) => r._field == "value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: {limit})
    '''
    rows = flux_query(flux)
    return [
        {
            "id":         "tel_influx",
            "session_id": session_id,
            "timestamp":  r.get("_time", datetime.now(timezone.utc)),
            "channel":    r.get("channel", ""),
            "value":      r.get("_value", 0.0),
            "unit":       None,
        }
        for r in rows
    ]


def get_summary(session_id: str) -> dict:
    """Per-channel summary stats."""
    flux = f'''
    data = from(bucket: "{INFLUX_BUCKET}")
        |> range(start: 0)
        |> filter(fn: (r) => r._measurement == "{MEAS_CHANNEL}")
        |> filter(fn: (r) => r.session_id == "{session_id}")
        |> filter(fn: (r) => r._field == "value")

    count = data |> group(columns: ["channel"]) |> count() |> yield(name: "count")
    min   = data |> group(columns: ["channel"]) |> min()   |> yield(name: "min")
    max   = data |> group(columns: ["channel"]) |> max()   |> yield(name: "max")
    last  = data |> group(columns: ["channel"]) |> last()  |> yield(name: "last")
    '''
    tables_raw = get_query_api()
    if tables_raw is None:
        return {"session_id": session_id, "total_points": 0, "channels": []}

    try:
        tables = tables_raw.query(flux, org=INFLUX_ORG)
    except Exception:
        return {"session_id": session_id, "total_points": 0, "channels": []}

    stats: dict = {}
    for table in tables:
        for record in table.records:
            ch = record.values.get("channel", "")
            name = record.values.get("result", "")
            val = record.values.get("_value", 0)
            if ch not in stats:
                stats[ch] = {}
            stats[ch][name] = val

    total = 0
    channel_list = []
    for ch_name, s in sorted(stats.items()):
        count = s.get("count", 0)
        total += count
        channel_list.append({
            "channel":      ch_name,
            "count":        count,
            "min":          round(s.get("min", 0), 4),
            "max":          round(s.get("max", 0), 4),
            "latest_value": round(s.get("last", 0), 4),
        })

    return {
        "session_id":   session_id,
        "total_points": total,
        "channels":     channel_list,
    }
