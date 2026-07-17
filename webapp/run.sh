#!/usr/bin/env bash
# Launch the Video Engine web frontend.
# Uses the atlas venv, which has the engine's runtime deps (edge_tts, requests, PIL, fastapi, uvicorn).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="$ROOT/atlas/venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "atlas venv python not found at $PY — falling back to system python3"
  PY="python3"
fi

PORT="${PORT:-8080}"
echo "Video Engine frontend → http://127.0.0.1:$PORT"
exec "$PY" -m uvicorn webapp.server:app --host 127.0.0.1 --port "$PORT"
