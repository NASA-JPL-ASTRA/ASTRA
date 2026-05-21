"""
AiSTRA Flask Query API (optional standalone dev server).

Four endpoints that wrap query.py and channel_search.py.
Run with: python app.py — listens on http://localhost:5001

Production / integrated UI: the same behavior is exposed on the FastAPI backend
as GET /api/query/* (see backend/app/routes/telemetry_query.py) and the React
page at /telemetry-query.
"""

from flask import Flask, request, jsonify, send_from_directory
from pathlib import Path
from query import get_channel_value, query_channel_range, get_recent_events
from channel_search import search_channel

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def require_params(args, *names):
    """
    Check that all required query parameters are present.
    Returns (values_dict, None) on success or (None, error_response) on failure.
    """
    missing = [n for n in names if not args.get(n)]
    if missing:
        return None, (jsonify({"error": f"Missing required parameters: {', '.join(missing)}"}), 400)
    return {n: args.get(n) for n in names}, None


def parse_float(args, name):
    """Parse a float query parameter. Returns (value, None) or (None, error_response)."""
    raw = args.get(name)
    if raw is None:
        return None, (jsonify({"error": f"Missing parameter: {name}"}), 400)
    try:
        return float(raw), None
    except ValueError:
        return None, (jsonify({"error": f"Parameter '{name}' must be a number, got: {raw}"}), 400)


# ── Endpoint 1: /channel ──────────────────────────────────────────────────────

@app.route("/api/query/channel")
def channel():
    """
    GET /channel?session=<id>&name=<channel>&at=<unix_ts>

    Returns the most recent value of a channel at or before `at`.

    Example:
        curl "http://localhost:5001/channel?session=test_4_motor_stall
              &name=motors.motor4_current&at=1772055750"

    Response:
        {"channel": "motors.motor4_current", "value": 0.512, "timestamp": 1772055749.98}

    404 if no data exists before `at` for this channel/session.
    """
    params, err = require_params(request.args, "session", "name")
    if err:
        return err

    at_time, err = parse_float(request.args, "at")
    if err:
        return err

    result = get_channel_value(
        session_id = params["session"],
        channel    = params["name"],
        at_time    = at_time,
    )

    if result is None:
        return jsonify({"error": f"No data found for channel '{params['name']}' "
                                 f"before timestamp {at_time} "
                                 f"in session '{params['session']}'"}), 404

    return jsonify(result)


# ── Endpoint 2: /range ────────────────────────────────────────────────────────

@app.route("/api/query/range")
def range_query():
    """
    GET /range?session=<id>&name=<channel>&t0=<unix_ts>&t1=<unix_ts>

    Returns min, max, mean, and last value over a time window.

    Example:
        curl "http://localhost:5001/range?session=test_4_motor_stall
              &name=motors.motor4_current&t0=1772055573&t1=1772055973"

    Response:
        {
          "channel": "motors.motor4_current",
          "session_id": "test_4_motor_stall",
          "start": 1776670526.0,
          "end": 1776670886.0,
          "min": 0.0,
          "max": 0.698,
          "mean": 0.421,
          "last": 0.0
        }

    404 if no data exists in the window.
    """
    params, err = require_params(request.args, "session", "name")
    if err:
        return err

    t0, err = parse_float(request.args, "t0")
    if err:
        return err

    t1, err = parse_float(request.args, "t1")
    if err:
        return err

    if t0 >= t1:
        return jsonify({"error": f"t0 ({t0}) must be less than t1 ({t1})"}), 400

    result = query_channel_range(
        session_id = params["session"],
        channel    = params["name"],
        start_time = t0,
        end_time   = t1,
    )

    if result is None:
        return jsonify({"error": f"No data found for channel '{params['name']}' "
                                 f"in window [{t0}, {t1}] "
                                 f"in session '{params['session']}'"}), 404

    return jsonify(result)


# ── Endpoint 3: /events ───────────────────────────────────────────────────────

@app.route("/api/query/events")
def events():
    """
    GET /events?session=<id>&t0=<unix_ts>&t1=<unix_ts>[&severity=warning][&limit=20]

    Returns EVR events in a time window.

    Example (all events):
        curl "http://localhost:5001/events?session=test_4_motor_stall
              &t0=1776670526&t1=1776670886"

    Example (warnings only):
        curl "http://localhost:5001/events?session=test_4_motor_stall
              &t0=1776670526&t1=1776670886&severity=warning"

    Response:
        [
          {
            "timestamp": 1776670526.28,
            "evr_name": "motors.current_limit_fault",
            "severity": "warning",
            "message": "Motor 4 current limit exceeded: 2.5A"
          }
        ]

    Returns [] (empty list) if no events match — not a 404.
    (An empty event log is a valid, normal result for a quiet session.)
    """
    params, err = require_params(request.args, "session")
    if err:
        return err

    t0, err = parse_float(request.args, "t0")
    if err:
        return err

    t1, err = parse_float(request.args, "t1")
    if err:
        return err

    severity = request.args.get("severity", "all")
    valid_severities = {"all", "warning", "activity_hi", "activity_lo", "command"}
    if severity not in valid_severities:
        return jsonify({"error": f"Invalid severity '{severity}'. "
                                 f"Must be one of: {', '.join(sorted(valid_severities))}"}), 400

    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        return jsonify({"error": "Parameter 'limit' must be an integer"}), 400

    result = get_recent_events(
        session_id = params["session"],
        start_time = t0,
        end_time   = t1,
        severity   = severity,
        limit      = limit,
    )

    return jsonify(result)


# ── Endpoint 4: /search ───────────────────────────────────────────────────────

@app.route("/api/query/search")
def search():
    """
    GET /search?q=<natural language>&k=<num results>

    Fuzzy-match channel names from a natural language description.
    Does not require a session_id — the channel dictionary is session-independent.

    Example:
        curl "http://localhost:5001/search?q=motor+temperature"
        curl "http://localhost:5001/search?q=position&k=5"

    Response:
        [
          {"channel": "motors.motor1_temperature", "score": 0.82},
          {"channel": "motors.motor2_temperature", "score": 0.81},
          {"channel": "motors.motor3_temperature", "score": 0.80}
        ]

    This is what allows the LLM to resolve "bus voltage" or "front motor temp"
    to an exact channel name before calling /channel or /range.
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Missing parameter: q"}), 400

    try:
        k = int(request.args.get("k", 3))
    except ValueError:
        return jsonify({"error": "Parameter 'k' must be an integer"}), 400

    results = search_channel(q, top_k=k)
    return jsonify(results)

# -- Root Page ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "aistra_telemetry_query_ui.html")


@app.route("/api-info")
def api_info():
    return {
        "service": "AiSTRA Telemetry Query API",
        "endpoints": ["/channel", "/range", "/events", "/search"],
    }


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("AiSTRA Telemetry Query API")
    print("Listening on http://localhost:5001")
    print("Endpoints: /channel  /range  /events  /search")
    app.run(host="0.0.0.0", port=5001, debug=True)