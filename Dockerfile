# Video Engine web app — deploys the FastAPI backend + frontend as one service.
# Uses Docker so ffmpeg (required by the render pipeline) is available.
FROM python:3.12-slim

# ffmpeg + ffprobe are needed by video_engine's renderer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the packages the web app actually needs.
COPY video_engine ./video_engine
COPY webapp ./webapp

ENV PYTHONUNBUFFERED=1

# Render provides $PORT; default to 10000 for local `docker run`.
CMD uvicorn webapp.server:app --host 0.0.0.0 --port ${PORT:-10000}
