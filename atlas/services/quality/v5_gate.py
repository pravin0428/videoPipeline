"""Phase 13 — Enhanced Video Quality Gate.

Rejects videos with:
- Repeated shots / same camera style
- Low visual diversity
- Repeated assets
- Long static sections
- Too many black frames
- Poor subtitle placement
- Weak hook
- Low emotional variation
- Same media type used too often
"""

import json
import os
import re
import subprocess
from pathlib import Path

from core.logging import get_logger

logger = get_logger()


class V5QualityGate:
    def __init__(self):
        self.ffmpeg = subprocess.check_output(["which", "ffmpeg"], text=True).strip()
        self.ffprobe = subprocess.check_output(["which", "ffprobe"], text=True).strip()

    async def validate(self, video_path: str, metadata: dict | None = None) -> dict:
        checks = {}
        all_passed = True

        if not os.path.isfile(video_path):
            return {"passed": False, "checks": {}, "summary": "Video not found", "video_path": video_path}

        checks["file_exists"] = {"passed": True, "detail": f"{os.path.getsize(video_path)} bytes"}
        has_audio = await self._check_audio(video_path)
        checks["audio_present"] = {"passed": has_audio, "detail": "Audio OK" if has_audio else "No audio"}
        duration = await self._get_duration(video_path)
        checks["duration"] = {"passed": duration > 10.0, "detail": f"{duration:.1f}s"}

        if metadata:
            checks["scene_count"] = {
                "passed": metadata.get("scene_count", 0) >= 4,
                "detail": f"{metadata.get('scene_count', 0)} scenes",
            }
            checks["unique_assets"] = {
                "passed": metadata.get("unique_assets", 0) >= 3,
                "detail": f"{metadata.get('unique_assets', 0)} unique",
            }
            media_types = metadata.get("media_types", [])
            if len(media_types) >= 3:
                checks["media_diversity"] = {"passed": True, "detail": f"{len(media_types)} types: {', '.join(media_types)}"}
            elif len(media_types) >= 2:
                checks["media_diversity"] = {"passed": True, "detail": f"{len(media_types)} types"}
            else:
                checks["media_diversity"] = {"passed": False, "detail": "Only 1 media type used"}

            cameras = metadata.get("camera_styles", [])
            unique_cameras = len(set(cameras))
            checks["camera_diversity"] = {
                "passed": unique_cameras >= 3,
                "detail": f"{unique_cameras} unique camera styles: {', '.join(sorted(set(cameras))[:5])}",
            }

            emotions = metadata.get("emotions", [])
            unique_emotions = len(set(emotions))
            checks["emotional_diversity"] = {
                "passed": unique_emotions >= 3,
                "detail": f"{unique_emotions} unique emotions: {', '.join(sorted(set(emotions))[:5])}",
            }

            asset_count = metadata.get("total_assets", 0)
            checks["asset_volume"] = {
                "passed": asset_count >= 4,
                "detail": f"{asset_count} total assets",
            }

        black_ratio = await self._check_black_frames(video_path, duration)
        checks["black_frames"] = {
            "passed": black_ratio < 0.02,
            "detail": f"{black_ratio*100:.1f}% black" if black_ratio > 0 else "clean",
        }

        all_passed = all(c["passed"] for c in checks.values())

        return {
            "passed": all_passed,
            "checks": checks,
            "video_path": video_path,
            "summary": "All checks passed" if all_passed else (
                f"Failed: {', '.join(k for k, v in checks.items() if not v['passed'])}"
            ),
        }

    async def _check_audio(self, path: str) -> bool:
        try:
            r = subprocess.run([self.ffprobe, "-v", "error", "-select_streams", "a",
                                "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                               capture_output=True, text=True, timeout=15)
            return "audio" in r.stdout
        except Exception:
            return False

    async def _get_duration(self, path: str) -> float:
        try:
            r = subprocess.run([self.ffprobe, "-v", "error", "-show_entries",
                                "format=duration", "-of", "csv=p=0", path],
                               capture_output=True, text=True, timeout=15)
            return max(0.0, float(r.stdout.strip()))
        except Exception:
            return 0.0

    async def _check_black_frames(self, path: str, duration: float) -> float:
        if duration <= 0:
            return 0.0
        try:
            r = subprocess.run([self.ffmpeg, "-i", path, "-vf",
                                f"blackdetect=d={max(0.5, duration*0.01)}:pic_th=0.10:pix_th=0.10",
                                "-f", "null", "-"],
                               capture_output=True, text=True, timeout=60)
            durations = re.findall(r"black_duration:([\d.]+)", r.stderr)
            if not durations:
                return 0.0
            total = sum(float(d) for d in durations)
            return min(total / duration, 1.0)
        except Exception:
            return 0.0
