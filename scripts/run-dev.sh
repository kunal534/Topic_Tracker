#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="$ROOT_DIR/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Virtual environment not found at $VENV_DIR" >&2
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

PORT="${PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"

if command -v docker >/dev/null 2>&1; then
  echo "Starting supporting services with Docker Compose..."
  docker compose up -d >/dev/null 2>&1 || true
fi

if [ ! -d web/node_modules ]; then
  echo "Installing web dependencies..."
  (cd web && npm install)
fi

cleanup() {
  local exit_code=$?
  for pid in "${pids[@]:-}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

declare -a pids=()

echo "Starting backend API..."
uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT" > "$ROOT_DIR/.tmp_backend.log" 2>&1 &
pids+=("$!")

echo "Starting Celery worker..."
celery -A app.tasks worker --loglevel=info --queues=collection --pool=solo > "$ROOT_DIR/.tmp_worker.log" 2>&1 &
pids+=("$!")

echo "Starting web frontend..."
(cd web && HOST=0.0.0.0 PORT="$WEB_PORT" BROWSER=none npm run watch:build) > "$ROOT_DIR/.tmp_web.log" 2>&1 &
pids+=("$!")

echo "All services started."
echo "- API: http://localhost:${PORT}"
echo "- Web UI: http://localhost:${WEB_PORT}"
echo "- Logs: $ROOT_DIR/.tmp_backend.log, $ROOT_DIR/.tmp_worker.log, $ROOT_DIR/.tmp_web.log"
echo "Press Ctrl+C to stop everything."

wait
