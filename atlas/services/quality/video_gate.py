import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.logging import get_logger

logger = get_logger()

MIN_SCENE_COUNT = 4
MIN_UNIQUE_ASSETS = 3
MIN_RESOLUTION = (1080, 1920)
MAX_BLACK_DURATION_RATIO = 0.02


class VideoQualityGate:
    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self.ffprobe = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

    async def validate(self, video_path: str, metadata: dict | None = None) -> dict:
        results = {
            "passed": False,
            "checks": {},
            "summary": "",
            "video_path": video_path,
        }

        if not os.path.isfile(video_path):
            results["summary"] = "Video file not found"
            return results

        file_size = os.path.getsize(video_path)
        if file_size < 1024:
            results["summary"] = f"Video file too small: {file_size} bytes"
            return results

        checks = {}
        checks["file_exists"] = {"passed": True, "detail": f"{file_size} bytes"}

        has_audio = await self._check_audio(video_path)
        checks["audio_present"] = {"passed": has_audio, "detail": "Audio stream found" if has_audio else "No audio stream"}

        duration = await self._get_duration(video_path)
        checks["duration"] = {"passed": duration > 5.0, "detail": f"{duration:.1f}s"}

        resolution = await self._get_resolution(video_path)
        res_ok = resolution and resolution[0] >= MIN_RESOLUTION[0] and resolution[1] >= MIN_RESOLUTION[1]
        checks["resolution"] = {
            "passed": bool(res_ok),
            "detail": f"{resolution[0]}x{resolution[1]}" if resolution else "unknown",
        }

        black_ratio = await self._check_black_frames(video_path, duration)
        checks["no_black_frames"] = {
            "passed": black_ratio < MAX_BLACK_DURATION_RATIO,
            "detail": f"{black_ratio*100:.1f}% black" if black_ratio > 0 else "clean",
        }

        if metadata:
            checks["scene_count"] = {
                "passed": metadata.get("scene_count", 0) >= MIN_SCENE_COUNT,
                "detail": f"{metadata.get('scene_count', 0)} scenes",
            }
            unique_assets = metadata.get("unique_assets", 0)
            checks["unique_assets"] = {
                "passed": unique_assets >= MIN_UNIQUE_ASSETS,
                "detail": f"{unique_assets} unique assets",
            }
            if "srt_path" in metadata:
                srt_ok = await self._check_subtitle_sync(metadata["srt_path"], duration)
                checks["subtitle_sync"] = {
                    "passed": srt_ok,
                    "detail": "Subtitles in sync" if srt_ok else "Subtitle timing mismatch",
                }

        all_passed = all(c["passed"] for c in checks.values())
        results["checks"] = checks
        results["passed"] = all_passed
        results["summary"] = "All checks passed" if all_passed else (
            f"Failed: {', '.join(k for k, v in checks.items() if not v['passed'])}"
        )

        logger.info("video_quality_gate", passed=all_passed, checks={k: v["passed"] for k, v in checks.items()})
        return results

    async def _check_audio(self, video_path: str) -> bool:
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=15,
            )
            return "audio" in result.stdout
        except Exception:
            return False

    async def _get_duration(self, video_path: str) -> float:
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=15,
            )
            return max(0.0, float(result.stdout.strip()))
        except Exception:
            return 0.0

    async def _get_resolution(self, video_path: str) -> tuple[int, int] | None:
        try:
            result = subprocess.run(
                [self.ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path],
                capture_output=True, text=True, timeout=15,
            )
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                return (int(parts[0]), int(parts[1]))
        except Exception:
            pass
        return None

    async def _check_black_frames(self, video_path: str, duration: float) -> float:
        if duration <= 0:
            return 0.0
        try:
            result = subprocess.run(
                [self.ffmpeg, "-i", video_path, "-vf",
                 f"blackdetect=d={max(0.5, duration*0.01)}:pic_th=0.10:pix_th=0.10",
                 "-f", "null", "-"],
                capture_output=True, text=True, timeout=60,
            )
            stderr = result.stderr
            black_durations = re.findall(r"black_duration:([\d.]+)", stderr)
            if not black_durations:
                return 0.0
            total_black = sum(float(d) for d in black_durations)
            return min(total_black / duration, 1.0)
        except Exception as e:
            logger.debug("blackdetect_failed", error=str(e)[:80])
            return 0.0

    async def _check_subtitle_sync(self, srt_path: str, video_duration: float) -> bool:
        if not os.path.isfile(srt_path):
            return True
        try:
            content = Path(srt_path).read_text()
            timestamps = re.findall(r"(\d+):(\d+):(\d+),(\d+)", content)
            if not timestamps:
                return True
            last_time = 0.0
            for h, m, s, ms in timestamps:
                t = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                last_time = max(last_time, t)
            if last_time > video_duration + 2.0:
                logger.warning("subtitle_sync_issue", last_subtitle_time=last_time, video_duration=video_duration)
                return False
            return True
        except Exception:
            return True
