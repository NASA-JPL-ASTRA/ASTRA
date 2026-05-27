#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_ROOT="${TELEMETRY_OUTPUT_ROOT:-$SCRIPT_DIR/telemetry-generator/output}"

if [[ -x "$REPO_ROOT/backend/venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/backend/venv/bin/python"
else
  PYTHON="${PYTHON:-python3}"
fi

if [[ ! -d "$OUTPUT_ROOT" ]]; then
  echo "Telemetry output folder not found: $OUTPUT_ROOT"
  echo "Generate logs first: cd telemetry/telemetry-generator && python generate_all.py"
  exit 1
fi

SCENARIOS=(
  "test_1_straight_line"
  "test_2_uphill"
  "test_3_stops_starts_turns"
  "test_4_motor_stall"
  "test_5_imu_malfunction"
  "test_6_command_error"
)

for scenario in "${SCENARIOS[@]}"; do
  log_dir="$OUTPUT_ROOT/$scenario"
  if [[ ! -d "$log_dir" ]]; then
    echo "Skipping missing scenario: $scenario ($log_dir)"
    continue
  fi
  "$PYTHON" "$SCRIPT_DIR/ingestor.py" --session "$scenario" --log-dir "$log_dir"
done

echo "Telemetry ingestion complete."
