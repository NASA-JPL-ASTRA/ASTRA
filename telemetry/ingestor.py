"""
AiSTRA Telemetry Ingestor
Reads channel.log and event.log files produced by the telemetry generator
and writes them into InfluxDB, tagged by session_id.

Usage:
    python ingestor.py --session test_4_motor_stall \
                       --log-dir ../telemetry-generator/output/test_4_motor_stall
"""

import argparse
import csv
import os
import time
from datetime import timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ── InfluxDB connection config ────────────────────────────────────────────────
# These match the docker run command above.
# In production, load these from environment variables or a config file.
INFLUX_URL    = "http://localhost:8086"
INFLUX_TOKEN  = "aistra-dev-token-12345"
INFLUX_ORG    = "aistra-org"
INFLUX_BUCKET = "telemetry"

# ── Measurements (table names in InfluxDB) ────────────────────────────────────
MEASUREMENT_CHANNEL = "telemetry_channel"
MEASUREMENT_EVENT   = "telemetry_event"

# ── Batch size — how many points to write at once ────────────────────────────
# Larger = faster ingestion, but uses more memory.
# 500 is a safe default for dev machines.
BATCH_SIZE = 500


def ingest_channel_log(write_api, session_id: str, log_path: str):
    """
    Read channel.log and write each row as an InfluxDB point.

    channel.log format (no header):
        timestamp, channel_name, value
        e.g.  1772055572.713749, motors.motor1_current, 0.506

    InfluxDB schema:
        measurement : telemetry_channel
        tag session_id : e.g. "test_4_motor_stall"
        tag channel    : e.g. "motors.motor1_current"
        field value    : float
        time           : nanoseconds
    """
    print(f"  Ingesting channel log: {log_path}")
    points = []
    rows_read = 0
    rows_skipped = 0

    with open(log_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 3:
                rows_skipped += 1
                continue

            timestamp_str, channel, value_str = row[0].strip(), row[1].strip(), row[2].strip()

            try:
                timestamp_ns = int(float(timestamp_str) * 1e9)   # seconds → nanoseconds
                value = float(value_str)
            except ValueError:
                # system.fault_code is a hex string like "0x0042" — store as a field tag instead
                # For the prototype we skip non-numeric values; Sprint 2 can handle them properly
                rows_skipped += 1
                continue

            point = (
                Point(MEASUREMENT_CHANNEL)
                .tag("session_id", session_id)
                .tag("channel", channel)
                .field("value", value)
                .time(timestamp_ns, WritePrecision.NS)
            )
            points.append(point)
            rows_read += 1

            # Flush in batches to avoid holding everything in memory
            if len(points) >= BATCH_SIZE:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
                points = []

    # Flush any remaining points
    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print(f"    Written: {rows_read} channel points  |  Skipped: {rows_skipped}")
    return rows_read


def ingest_event_log(write_api, session_id: str, log_path: str):
    """
    Read event.log and write each row as an InfluxDB point.

    event.log format (no header):
        timestamp, evr_name, severity, message
        e.g.  1772055572.613, drive.start_forward, activity_hi, Drive command received

    InfluxDB schema:
        measurement : telemetry_event
        tag session_id : e.g. "test_4_motor_stall"
        tag evr_name   : e.g. "drive.start_forward"
        tag severity   : e.g. "activity_hi"
        field message  : string
        time           : nanoseconds
    """
    print(f"  Ingesting event log:   {log_path}")
    points = []
    rows_read = 0
    rows_skipped = 0

    with open(log_path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                rows_skipped += 1
                continue

            timestamp_str = row[0].strip()
            evr_name      = row[1].strip()
            severity      = row[2].strip()
            message       = ",".join(row[3:]).strip()   # message may contain commas

            try:
                timestamp_ns = int(float(timestamp_str) * 1e9)
            except ValueError:
                rows_skipped += 1
                continue

            point = (
                Point(MEASUREMENT_EVENT)
                .tag("session_id", session_id)
                .tag("evr_name", evr_name)
                .tag("severity", severity)
                .field("message", message)
                .time(timestamp_ns, WritePrecision.NS)
            )
            points.append(point)
            rows_read += 1

    if points:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)

    print(f"    Written: {rows_read} events  |  Skipped: {rows_skipped}")
    return rows_read


def ingest_session(session_id: str, log_dir: str):
    """Ingest both log files for a single test session."""
    channel_log = os.path.join(log_dir, "channel.log")
    event_log   = os.path.join(log_dir, "event.log")

    if not os.path.exists(channel_log):
        raise FileNotFoundError(f"channel.log not found at {channel_log}")
    if not os.path.exists(event_log):
        raise FileNotFoundError(f"event.log not found at {event_log}")

    print(f"\nIngesting session '{session_id}' from {log_dir}")
    start = time.time()

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    channel_count = ingest_channel_log(write_api, session_id, channel_log)
    event_count   = ingest_event_log(write_api, session_id, event_log)

    client.close()
    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s — {channel_count} channel points + {event_count} events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest AiSTRA telemetry logs into InfluxDB")
    parser.add_argument("--session",  required=True, help="Session ID tag (e.g. test_4_motor_stall)")
    parser.add_argument("--log-dir",  required=True, help="Directory containing channel.log and event.log")
    args = parser.parse_args()

    ingest_session(args.session, args.log_dir)