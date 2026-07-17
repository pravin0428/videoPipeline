#!/usr/bin/env bash
set -euo pipefail

echo "=== Atlas - Knowledge Research Engine ==="

echo ""
echo "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "python3 is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 && DOCKER_AVAILABLE=true || DOCKER_AVAILABLE=false

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

echo "Installing Python dependencies..."
pip3 install -q -r requirements.txt

LOCAL_MODE=false
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo ""
    echo "Docker is available."
    echo "Options:"
    echo "  1) Run with Docker Compose (full stack)"
    echo "  2) Run locally (requires PostgreSQL + Ollama)"
    read -rp "Choose [1/2]: " choice
    case "$choice" in
        1)
            echo "Starting with Docker Compose..."
            docker compose up --build
            exit 0
            ;;
        *)
            LOCAL_MODE=true
            ;;
    esac
else
    LOCAL_MODE=true
fi

if [ "$LOCAL_MODE" = true ]; then
    echo ""
    echo "Running migrations..."
    alembic upgrade head

    echo ""
    echo "Starting API server..."
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
fi
