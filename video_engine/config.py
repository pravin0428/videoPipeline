from __future__ import annotations

from pathlib import Path

from video_engine.models import (
    DocumentaryProfile,
    CameraMovement,
    CameraAngle,
    LensType,
    TimeOfDay,
    Weather,
    Mood,
    VisualEffect,
    MotionIntensity,
    CompositionType,
)

PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_PROFILE = DocumentaryProfile.NATURALISTIC

FPS = 30
RESOLUTION = "1080x1920"
TRANSITION_DURATION = 0.5

TTS_VOICE = "hi-IN-SwaraNeural"
TTS_BASE_RATE = "+0%"
TTS_VOLUME = "+0%"
TTS_PITCH = "+0Hz"

PEXELS_PER_PAGE = 15
PEXELS_MIN_DURATION = 5
PEXELS_ORIENTATION = "portrait"
PEXELS_VIDEO_QUALITY = "medium"
PEXELS_LOCALE = "en-US"
PEXELS_CACHE_DIR = PROJECT_ROOT / ".pexels_cache"

SUBJECT_FALLBACK_COLOR = (20, 20, 40)
TEXT_FALLBACK_BG = (10, 10, 30)

RETRY_COUNT = 3
RETRY_DELAY_BASE = 1.0
RETRY_DELAY_MAX = 10.0
RETRY_QUERY_REFINEMENTS = [
    "cinematic shot",
    "professional footage",
    "stock footage",
    "nature documentary",
    "drone view",
]

MIN_QUALITY_SCORE = 60
SCORE_WEIGHTS = {
    "relevance": 0.35,
    "camera_match": 0.15,
    "lighting_match": 0.10,
    "motion_match": 0.10,
    "continuity": 0.10,
    "composition": 0.10,
    "resolution": 0.05,
    "duration_fit": 0.05,
}

SIMILARITY_BOOST_THRESHOLD = 0.6
SIMILARITY_BOOST_FACTOR = 1.2

CONTINUITY_FIELDS = [
    "time_of_day",
    "weather",
    "mood",
    "color_palette",
    "camera_movement",
    "camera_angle",
    "lens",
    "depth_of_field",
    "composition",
]

NORMALIZE_VIDEO_CODEC = "libx264"
NORMALIZE_PIX_FMT = "yuv420p"
CONCAT_DEMUXER_TEMP_DIR = PROJECT_ROOT / ".concat_tmp"

SUBTITLE_FONT = "/System/Library/Fonts/Supplemental/Devanagari Sang MN.ttc"
SUBTITLE_FONT_SIZE = 28
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_OUTLINE_COLOR = "black"
SUBTITLE_OUTLINE_WIDTH = 1
SUBTITLE_MARGIN_V = 50

OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_EXTENSION = ".mp4"

CACHE_DIRS = {
    "normalized": PROJECT_ROOT / ".normalized_cache",
}

PROGRESS_SYMBOLS = {
    "start": "\u25b6",
    "done": "\u2714",
    "warn": "\u26a0",
    "fail": "\u2718",
    "skip": "\u21b7",
    "arrow": "\u2192",
}

PROVIDER = "pexels"
PROVIDER_FALLBACK_ORDER = ["veo", "kling", "runway", "pixverse", "hailuo", "pexels"]
PROVIDER_CACHE_DIR = PROJECT_ROOT / ".provider_cache"
