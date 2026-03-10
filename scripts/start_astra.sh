#!/bin/bash
#
# ASTRA one-click start: Whisper API + Backend (Frontend optional)
# Usage: ./scripts/start_astra.sh
#        ASTRA_BACKEND_PATH=/path/to/ASTRA-dev-feature1 ./scripts/start_astra.sh
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHISPER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Backend path: prefer local ./backend, then env var, then legacy locations
if [ -z "$ASTRA_BACKEND_PATH" ]; then
  for p in "$WHISPER_ROOT/backend" \
           "$WHISPER_ROOT/../ASTRA-dev-feature1/backend" \
           "$HOME/Desktop/ASTRA-dev-feature1/backend"; do
    if [ -d "$p" ]; then
      ASTRA_BACKEND_PATH="$p"
      break
    fi
  done
fi

echo "=== ASTRA One-Click Start ==="
echo "Whisper: $WHISPER_ROOT"
echo "Backend: $ASTRA_BACKEND_PATH"
echo ""

# Kill child processes on exit
cleanup() {
  echo ""
  echo "Stopping..."
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Whisper API (8001)
cd "$WHISPER_ROOT"
# To clear task queue on start: CLEAR_QUEUE_ON_START=1 ./scripts/start_astra.sh
if [ -n "$CLEAR_QUEUE_ON_START" ]; then
  rm -f WhisperServiceAPI.db
  echo "Cleared task queue (removed WhisperServiceAPI.db)"
fi
echo "[1/2] Starting Whisper API (port 8001)..."
# FILTER_HALLUCINATION=false disables result filtering for live transcription
FILTER_HALLUCINATION="${FILTER_HALLUCINATION:-false}" PORT=8001 python start.py &
WHISPER_PID=$!

# 2. Start ASTRA Backend (8000)
if [ -d "$ASTRA_BACKEND_PATH" ]; then
  echo "[2/2] Starting ASTRA Backend (port 8000)..."
  (
    cd "$ASTRA_BACKEND_PATH"
    export WHISPER_API_URL="${WHISPER_API_URL:-http://127.0.0.1:8001}"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ) &
  BACKEND_PID=$!
else
  echo "[2/2] Skipping Backend (not found: $ASTRA_BACKEND_PATH)"
fi

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
for i in {1..15}; do
  if curl -s http://127.0.0.1:8001/health >/dev/null 2>&1; then
    echo "  Whisper API: ready"
    break
  fi
  sleep 1
  [ $i -eq 15 ] && echo "  Whisper API: startup timeout"
done

if [ -d "$ASTRA_BACKEND_PATH" ]; then
  for i in {1..10}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
      echo "  ASTRA Backend: ready"
      break
    fi
    sleep 1
    [ $i -eq 10 ] && echo "  ASTRA Backend: startup timeout"
  done
fi

echo ""
echo "=========================================="
echo "Services started"
echo "  - Whisper API: http://127.0.0.1:8001"
echo "  - ASTRA Backend: http://127.0.0.1:8000"
echo ""
echo "Run realtime demo:"
echo "  python realtime_demo.py --backend-url http://127.0.0.1:8000"
echo ""
# Prefer local frontend, then sibling of backend
FRONTEND_DIR="$WHISPER_ROOT/frontend"
if [ ! -d "$FRONTEND_DIR" ] && [ -n "$ASTRA_BACKEND_PATH" ]; then
  FRONTEND_DIR="$(cd "$ASTRA_BACKEND_PATH/../frontend" 2>/dev/null && pwd)"
fi
if [ -n "$FRONTEND_DIR" ] && [ -d "$FRONTEND_DIR" ]; then
  echo "Or start Frontend (in another terminal):"
  echo "  cd $FRONTEND_DIR && npm run dev"
fi
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop all services"
wait
