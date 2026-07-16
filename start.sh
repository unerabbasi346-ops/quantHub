#!/bin/bash
# Perf pass: fast, reliable single-terminal startup. Real readiness polling
# against both services, run CONCURRENTLY (the old version waited on backend
# fully before even starting the frontend wait loop) — bounded by a real
# timeout, so a broken start fails fast and loud instead of always printing
# "ready" whether or not anything actually came up, and instead of the old
# global `taskkill //IM node.exe` / `//IM python.exe` on Ctrl+C, which killed
# every node/python process on the machine, not just this app's.
set -uo pipefail
cd "$(dirname "$0")"

BACKEND_PROBE_URL="http://localhost:8000/v1/assets"
FRONTEND_PROBE_URL="http://localhost:3000"
TIMEOUT_S=15
LOG_DIR="/tmp/quanthub-logs"
mkdir -p "$LOG_DIR"

fail() {
  echo "" >&2
  echo "ERROR: $1" >&2
  exit 1
}

# curl without -f: any HTTP response (even 4xx/5xx) means the server is up
# and routing requests — neither service is guaranteed a fixed 200-at-a-
# known-path health route, so "responded at all" is the real readiness signal.
responding() {
  curl -s -o /dev/null --max-time 1 "$1"
}

echo "Starting database..."
(cd docker && docker compose up -d) || fail "docker compose up failed — is Docker running?"

echo "Starting backend..."
(cd backend && uv run python -m uvicorn quant_hub.main:app --reload --port 8000 > "$LOG_DIR/backend.log" 2>&1 &)

echo "Starting frontend..."
(cd frontend && npm run dev > "$LOG_DIR/frontend.log" 2>&1 &)

echo "Waiting for services (up to ${TIMEOUT_S}s)..."
backend_ready=0
frontend_ready=0
elapsed=0
while [ "$elapsed" -lt "$TIMEOUT_S" ]; do
  if [ "$backend_ready" -eq 0 ] && responding "$BACKEND_PROBE_URL"; then
    backend_ready=1
    echo "  backend  responding (${elapsed}s)"
  fi
  if [ "$frontend_ready" -eq 0 ] && responding "$FRONTEND_PROBE_URL"; then
    frontend_ready=1
    echo "  frontend responding (${elapsed}s)"
  fi
  [ "$backend_ready" -eq 1 ] && [ "$frontend_ready" -eq 1 ] && break
  sleep 1
  elapsed=$((elapsed + 1))
done

if [ "$backend_ready" -eq 0 ]; then
  echo "ERROR: backend did not respond within ${TIMEOUT_S}s." >&2
  echo "Last 20 lines of $LOG_DIR/backend.log:" >&2
  tail -n 20 "$LOG_DIR/backend.log" >&2
  exit 1
fi
if [ "$frontend_ready" -eq 0 ]; then
  echo "ERROR: frontend did not respond within ${TIMEOUT_S}s." >&2
  echo "Last 20 lines of $LOG_DIR/frontend.log:" >&2
  tail -n 20 "$LOG_DIR/frontend.log" >&2
  exit 1
fi

echo ""
echo "Ready at http://localhost:3000"
echo "Backend logs:  $LOG_DIR/backend.log"
echo "Frontend logs: $LOG_DIR/frontend.log"
echo "Press Ctrl+C to stop watching (background services keep running)."
wait
