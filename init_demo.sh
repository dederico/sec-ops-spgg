#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
START_NGROK="${START_NGROK:-false}"
NGROK_BIN="${NGROK_BIN:-ngrok}"

cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "[1/4] Installing backend dependencies"
.venv/bin/pip install -r backend/requirements.txt

echo "[2/4] Installing frontend dependencies"
cd frontend
npm install

echo "[3/4] Building frontend for single-port serving"
npm run build
cd "$ROOT_DIR"

echo "[4/4] Starting backend on http://$HOST:$BACKEND_PORT"
echo "Command Center: http://localhost:$BACKEND_PORT/"
echo "Dashboard:      http://localhost:$BACKEND_PORT/dashboard"
echo "Mobile Bridge:  http://localhost:$BACKEND_PORT/mobile-bridge"
if [ "$START_NGROK" = "true" ]; then
  .venv/bin/uvicorn backend.main:app --host "$HOST" --port "$BACKEND_PORT" &
  APP_PID=$!

  cleanup() {
    kill "$APP_PID" >/dev/null 2>&1 || true
    if [ -n "${NGROK_PID:-}" ]; then
      kill "$NGROK_PID" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT INT TERM

  sleep 2
  echo "[ngrok] Starting tunnel on port $BACKEND_PORT"
  "$NGROK_BIN" http "$BACKEND_PORT" >/tmp/certivision-ngrok.log 2>&1 &
  NGROK_PID=$!
  sleep 3

  if command -v curl >/dev/null 2>&1; then
    NGROK_URL="$(curl -s http://127.0.0.1:4040/api/tunnels | python3 - <<'PY'
import json, sys
data = json.load(sys.stdin)
for tunnel in data.get("tunnels", []):
    url = tunnel.get("public_url", "")
    if url.startswith("https://"):
        print(url)
        break
PY
)"
    if [ -n "$NGROK_URL" ]; then
      echo "[ngrok] Public URL: $NGROK_URL"
      echo "[ngrok] Command Center: $NGROK_URL/"
      echo "[ngrok] Mobile Bridge:  $NGROK_URL/mobile-bridge"
      echo "[ngrok] Dashboard:      $NGROK_URL/dashboard"
    else
      echo "[ngrok] Tunnel started, but public URL could not be read automatically."
      echo "[ngrok] Inspect http://127.0.0.1:4040"
    fi
  fi

  wait "$APP_PID"
else
  exec .venv/bin/uvicorn backend.main:app --host "$HOST" --port "$BACKEND_PORT"
fi
