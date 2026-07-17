# Atlas

Phase 2 of an autonomous knowledge-to-video platform — research engine → Hindi YouTube Shorts script generation.

**Topic → Discovery → Queue → Research → Fact Extraction → Knowledge Storage → Script Generation → TTS (Hindi Audio)**

## Architecture

```
Topic / Discovery
      │
      ▼
 Queue (pending → processing → completed/failed)
      │
      ▼
 Research Engine ───► Wikipedia API
                      Wikidata API
                      Wikimedia Commons API
                      GeoNames API
      │
      ▼
 LLM (Qwen3:8B via Ollama) ───► Fact Extraction
      │
      ▼
 Knowledge Database (PostgreSQL)
      │
      ▼
 Script Generator ───► Ollama Qwen3:8B (Hindi Shorts)
      │
      ▼
 Scripts Table (PostgreSQL)
      │
      ▼
 TTS Engine ───► Edge-TTS (Hindi Neural Voices)
      │
      ▼
 Audio Table (PostgreSQL) + MP3 Files
```

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL 16
- SQLAlchemy 2.0 (async)
- Alembic
- Pydantic v2
- httpx (async HTTP)
- Ollama + Qwen3:8B
- structlog

## Quick Start

### Docker (recommended)

```bash
docker compose up --build
```

This starts PostgreSQL, Ollama (with Qwen3:8B), and the API server.

### Local Development

```bash
# 1. Copy environment configuration
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Start the API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Requires PostgreSQL running locally and Ollama serving `qwen3:8b`.

## API Endpoints

### Create Topic

```
POST /api/topics
Content-Type: application/json

{
  "name": "Ajanta Caves",
  "entity_type": "landmark"
}
```

Response: `201 { "topic_id": "uuid" }`

Supported entity types: `country`, `state`, `district`, `city`, `town`, `village`, `mountain`, `river`, `lake`, `forest`, `island`, `temple`, `fort`, `castle`, `museum`, `historical_event`, `festival`, `culture`, `landmark`

### Run Research

```
POST /api/topics/{topic_id}/research
```

Response: `200 { "status": "completed" }`

### Get Topic Data

```
GET /api/topics/{topic_id}
```

Response:
```json
{
  "summary": "string",
  "facts": [
    { "fact": "string", "source": "string", "confidence_score": 0.0 }
  ],
  "images": [
    { "image_url": "string", "source": "string" }
  ]
}
```

### Queue Management

```
# List queue items (with optional status filter)
GET /api/queue?status=pending&limit=10

# Get specific queue item
GET /api/queue/{item_id}

# Process next pending item
POST /api/queue/process-next
```

### Topic Discovery (GeoNames)

```
POST /api/discover
Content-Type: application/json

{
  "query": "mountain",
  "entity_type": "mountain",
  "country_filter": "India",
  "max_results": 20
}
```

Response:
```json
{
  "query": "mountain",
  "entity_type": "mountain",
  "total_found": 15,
  "enqueued": 12,
  "skipped": 3,
  "results": [
    { "name": "K2", "entity_type": "mountain", "country": "PK", "geoname_id": 1262259 }
  ],
  "source": "geonames_discovery"
}
```

### Images

```
# List images for a topic
GET /api/images/{topic_id}

# Download topic images to local storage
POST /api/images/{topic_id}/download
```

### Script Generation (Phase 2)

```
# Generate a Hindi YouTube Shorts script
POST /api/topics/{topic_id}/script
Content-Type: application/json

{
  "script_type": "SHORTS_60",
  "max_facts": 10
}
```

Response: `200`
```json
{
  "id": "uuid",
  "topic_id": "uuid",
  "script_type": "SHORTS_60",
  "title": "अजंता की गुफाएं - एक अद्भुत यात्रा",
  "hook": "क्या आप जानते हैं कि 2000 साल पहले बनी ये गुफाएं...",
  "script_text": "अजंता की गुफाएं महाराष्ट्र में स्थित हैं...",
  "estimated_duration": 50,
  "quality_score": 92.5
}
```

```
# Get the latest generated script for a topic
GET /api/topics/{topic_id}/script
```

### Text-to-Speech (TTS) — Phase 3

```
# Generate Hindi audio from the latest script
POST /api/topics/{topic_id}/tts
Content-Type: application/json

{
  "voice": "hi-IN-SwaraNeural",
  "rate": "+0%",
  "pitch": "+0Hz"
}
```

Response: `200`
```json
{
  "id": "uuid",
  "topic_id": "uuid",
  "script_id": "uuid",
  "audio_path": "/home/atlas/.atlas/audio/abc123_hi-IN-SwaraNeural.mp3",
  "duration_seconds": 52.3,
  "file_size": 84521,
  "mime_type": "audio/mp3",
  "voice": "hi-IN-SwaraNeural"
}
```

```
# Get the latest generated audio metadata
GET /api/topics/{topic_id}/tts
```

#### TTS Provider: Edge-TTS

Uses Microsoft Edge's free neural TTS service. No API key required. Supports Hindi with multiple voices:

| Voice | Description |
|-------|-------------|
| `hi-IN-SwaraNeural` | Female, neutral (default) |
| `hi-IN-MadhurNeural` | Male, neutral |
| `hi-IN-AaravNeural` | Male, enthusiastic |
| `hi-IN-IshaniNeural` | Female, enthusiastic |

Audio files are stored locally at `{APP_DATA_DIR}/audio/`.

### Script Quality Scoring

Scripts are scored on a 0-100 scale based on:

| Criterion | Weight |
|-----------|--------|
| Base score | 40 |
| Title quality (≥5 chars) | 10 |
| Hook quality (≥10 chars) | 15 |
| Length (60-110 words) | 10 |
| Duration (45-60s) | 10 |
| Fact coverage | 15 |
| **Maximum** | **100** |

## Research Pipeline

1. **Fetch** data from Wikipedia + Wikidata + Wikimedia Commons + GeoNames
2. **Merge** responses into unified document
3. **Extract** knowledge via Ollama (Qwen3:8B) using structured prompt
4. **Store** facts with confidence scores
5. **Store** images from Commons

### Confidence Scoring

| Source | Points |
|--------|--------|
| Wikipedia | +25 |
| Wikidata | +25 |
| Commons | +20 |
| GeoNames | +15 |
| **Maximum** | **85** |

Facts get de-duplicated by text and scored with the sum of all provider weights that contributed to the research run.

## Discovery Pipeline

1. **Query** GeoNames API for geographic features matching a keyword
2. **Filter** by entity type and/or country (optional)
3. **Skip** topics already in the database (by name)
4. **Create** new Topic records
5. **Enqueue** them for research processing

## Project Structure

```
atlas/
├── api/                  # FastAPI routes and app
├── core/                 # Config, logging, database
├── models/               # SQLAlchemy ORM models
├── schemas/              # Pydantic request/response schemas
├── repositories/         # Data access layer (repository pattern)
├── services/             # Business logic
│   ├── commons/          # Wikimedia Commons API provider
│   ├── geonames/         # GeoNames API provider
│   ├── wikipedia/        # Wikipedia API provider
│   ├── wikidata/         # Wikidata API provider
│   ├── script/           # Hindi Shorts script generator
│   ├── tts/              # TTS provider (Edge-TTS)
│   └── llm/              # Ollama LLM provider
├── pipelines/            # Research + Discovery orchestration
├── tests/                # Unit + integration tests
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── docker/               # Docker config
└── docs/                 # Documentation
```

## Testing

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://atlas:atlas@localhost:5432/atlas` | Async database URL |
| `DATABASE_URL_SYNC` | `postgresql://atlas:atlas@localhost:5432/atlas` | Sync database URL (for Alembic) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen3:8b` | LLM model name |
| `GEONAMES_USERNAME` | `demo` | GeoNames API username |
| `LOG_LEVEL` | `INFO` | Logging level |
| `APP_HOST` | `0.0.0.0` | API bind address |
| `APP_PORT` | `8000` | API port |
| `APP_DATA_DIR` | `~/.atlas` | Local data directory (images, audio, etc.) |
| `TTS_DEFAULT_VOICE` | `hi-IN-SwaraNeural` | Default Edge-TTS Hindi voice |
| `TTS_DEFAULT_RATE` | `+0%` | Default speaking rate |
| `TTS_DEFAULT_PITCH` | `+0Hz` | Default pitch |

## What's NOT Included (Phase 4+)

- Video generation
- Subtitle generation
- YouTube upload
- Thumbnail generation
