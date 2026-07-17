from __future__ import annotations

import os
import subprocess
import shutil
import time
from typing import Optional

import requests

from video_engine.providers.base_provider import BaseProvider, VideoAsset
from video_engine.utils.ffmpeg import get_duration
from video_engine.utils.logging import LOG
from video_engine.config import (
    PEXELS_PER_PAGE,
    PEXELS_ORIENTATION,
    PEXELS_VIDEO_QUALITY,
    TEXT_FALLBACK_BG,
)


class PexelsProvider(BaseProvider):
    provider_name = "pexels"

    VIDEO_URL = "https://api.pexels.com/videos/search"
    PHOTO_URL = "https://api.pexels.com/v1/search"
    FONT_PATH = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"

    def __init__(self, config: Optional[dict] = None) -> None:
        super().__init__(config)
        self._api_key: str = ""
        self._resolution: str = "1080x1920"

    def initialize(self) -> None:
        self._api_key = (self.config.get("api_key") or
                         os.environ.get("PEXELS_API_KEY", ""))
        self._resolution = self.config.get("resolution", "1080x1920")
        self._initialized = True
        if not self._api_key:
            LOG.warn("PexelsProvider: PEXELS_API_KEY not set — will use fallback text scenes")

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            headers = {"Authorization": self._api_key}
            resp = requests.get(
                self.VIDEO_URL,
                headers=headers,
                params={"query": "nature", "per_page": 1},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def supports_images(self) -> bool:
        return True

    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        if not self._initialized:
            raise RuntimeError("PexelsProvider not initialized — call initialize() first")

        opts = options or {}
        output_path = opts.get("output_path", "")
        target_duration = opts.get("duration", 5.0)
        shot_type = opts.get("shot_type", "")
        query = opts.get("query_hint", prompt)

        if not output_path:
            raise ValueError("PexelsProvider requires output_path in options")

        start_time = time.time()
        asset = VideoAsset(
            provider_name=self.provider_name,
            duration=target_duration,
            fps=opts.get("fps", 30),
            width=self._target_w(),
            height=self._target_h(),
        )

        queries = self._build_queries(query, shot_type)

        for q in queries:
            result = self._try_video(q, output_path, target_duration)
            if result is not None:
                asset.local_path = output_path
                asset.metadata = result
                self._record_generation(asset, start_time)
                return asset

        for q in queries:
            result = self._try_photo(q, output_path, target_duration)
            if result is not None:
                asset.local_path = output_path
                asset.metadata = result
                self._record_generation(asset, start_time)
                LOG.warn(f"    Ken Burns from photo ({target_duration:.1f}s)")
                return asset

        self._create_fallback_scene(output_path, target_duration, ["...", query])
        asset.local_path = output_path
        self._record_generation(asset, start_time)
        LOG.warn(f"    Fallback text scene ({target_duration:.1f}s)")
        return asset

    def _target_w(self) -> int:
        return int(self._resolution.split("x")[0])

    def _target_h(self) -> int:
        return int(self._resolution.split("x")[1])

    def _target_dims(self) -> tuple[int, int]:
        parts = self._resolution.split("x")
        return int(parts[0]), int(parts[1])

    def _build_queries(self, base_query: str, shot_type: str) -> list[str]:
        queries = [base_query]
        modifiers = {
            "aerial": ["aerial view", "drone shot"],
            "wide": ["wide angle", "panorama"],
            "medium": ["medium shot"],
            "close_up": ["close up", "macro"],
            "detail": ["texture", "close up detail"],
            "macro": ["extreme close up"],
            "transition": ["time lapse"],
        }
        for mod in modifiers.get(shot_type, []):
            if mod not in queries[0].lower():
                queries.append(f"{mod} {queries[0]}")
        return queries

    def _try_video(self, query: str, output_path: str, target_duration: float) -> Optional[dict]:
        if not self._api_key:
            return None
        try:
            headers = {"Authorization": self._api_key}
            params = {
                "query": query,
                "per_page": PEXELS_PER_PAGE,
                "orientation": PEXELS_ORIENTATION,
                "size": PEXELS_VIDEO_QUALITY,
            }
            resp = requests.get(self.VIDEO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            if not videos:
                return None

            # Pick the SMALLEST file that still covers the target resolution.
            # Grabbing the largest HD variant means huge downloads + slow re-encodes
            # (painful on low-CPU hosts); a file at/just above target is plenty.
            target_w, target_h = self._target_dims()
            adequate: list[dict] = []
            fallback: list[dict] = []
            for v in videos:
                dur = v.get("duration", 0)
                if dur < target_duration * 0.8:
                    continue
                for vf in v.get("video_files", []):
                    w, h = vf.get("width") or 0, vf.get("height") or 0
                    if w <= 0 or h <= 0:
                        continue
                    portrait = 0.5 <= (w / h) <= 0.65
                    entry = {"file": vf, "area": w * h, "duration": dur, "portrait": portrait}
                    if w >= target_w * 0.9 and h >= target_h * 0.9:
                        adequate.append(entry)
                    else:
                        fallback.append(entry)

            if adequate:
                # smallest file that covers the target, preferring portrait aspect
                adequate.sort(key=lambda e: (not e["portrait"], e["area"]))
                best = adequate[0]
            elif fallback:
                # nothing big enough — take the largest available
                fallback.sort(key=lambda e: (not e["portrait"], -e["area"]))
                best = fallback[0]
            else:
                return None

            dl_resp = requests.get(best["file"]["link"], timeout=60)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)

            target_w, target_h = self._target_dims()
            trim_duration = min(target_duration, best["duration"])
            trimmed_path = output_path.replace(".mp4", "_trimmed.mp4")
            scale_filter = (
                f"scale='max({target_w},iw*{target_h}/ih)':'max({target_h},ih*{target_w}/iw)',"
                f"crop={target_w}:{target_h}"
            )
            subprocess.run([
                "ffmpeg", "-y", "-i", output_path,
                "-t", str(trim_duration),
                "-vf", scale_filter,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "ultrafast", "-crf", "23",
                trimmed_path,
            ], capture_output=True, timeout=180)
            if os.path.exists(trimmed_path) and os.path.getsize(trimmed_path) > 1000:
                os.replace(trimmed_path, output_path)

            actual_dur = get_duration(output_path)
            if actual_dur > 0 and actual_dur < target_duration * 0.85:
                self._pad_video(output_path, target_duration)

            return {
                "source": "pexels_video",
                "query": query,
                "original_duration": best["duration"],
                "pexels_video_id": best["file"].get("id", ""),
            }
        except Exception:
            return None

    def _try_photo(self, query: str, output_path: str, target_duration: float) -> Optional[dict]:
        if not self._api_key:
            return None
        try:
            headers = {"Authorization": self._api_key}
            params = {"query": query, "per_page": 5, "orientation": PEXELS_ORIENTATION}
            resp = requests.get(self.PHOTO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                return None
            best = max(photos, key=lambda p: p.get("width", 0) * p.get("height", 0))
            dl_resp = requests.get(best["src"]["large"], timeout=60)
            dl_resp.raise_for_status()
            photo_path = output_path.replace(".mp4", ".jpg")
            with open(photo_path, "wb") as f:
                f.write(dl_resp.content)
            self._ken_burns_effect(photo_path, output_path, target_duration)
            if os.path.exists(photo_path):
                os.remove(photo_path)
            return {
                "source": "pexels_photo_ken_burns",
                "query": query,
                "photo_id": best.get("id", ""),
            }
        except Exception:
            return None

    def _ken_burns_effect(self, image_path: str, output_path: str, duration: float):
        target_w, target_h = self._target_dims()
        zoom_factor = 1.08
        src_w, src_h = int(target_w * zoom_factor), int(target_h * zoom_factor)
        base_dir = os.path.dirname(output_path)
        scaled_path = os.path.join(base_dir, "_scaled.png")

        subprocess.run([
            "ffmpeg", "-y", "-i", image_path,
            "-vf", f"scale={src_w}:{src_h}:force_original_aspect_ratio=increase,crop={src_w}:{src_h}",
            "-frames:v", "1", scaled_path,
        ], capture_output=True, timeout=60)

        pan_pixels = src_w - target_w
        x_expr = f"{pan_pixels}*t/{duration}"
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", scaled_path,
            "-vf", f"crop={target_w}:{target_h}:{x_expr}:0,format=yuv420p",
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-crf", "23",
            output_path,
        ], capture_output=True, timeout=120)

        if os.path.exists(scaled_path):
            os.remove(scaled_path)

    def _pad_video(self, video_path: str, target_duration: float):
        actual_dur = get_duration(video_path)
        if actual_dur <= 0:
            return
        pad_path = video_path.replace(".mp4", "_pad.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={target_duration - actual_dur}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "ultrafast", "-crf", "23",
            pad_path,
        ], capture_output=True, timeout=60)
        shutil.move(pad_path, video_path)

    def _create_fallback_scene(self, output_path: str, duration: float, text_lines: list[str]):
        from PIL import Image, ImageDraw, ImageFont
        target_w, target_h = self._target_dims()
        img = Image.new("RGB", (target_w, target_h), TEXT_FALLBACK_BG)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(self.FONT_PATH, 48)
        except Exception:
            font = ImageFont.load_default()
        joined = "\n".join(text_lines)
        bbox = draw.multiline_textbbox((0, 0), joined, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (target_w - tw) // 2
        y = (target_h - th) // 2
        draw.multiline_text((x, y), joined, fill=(255, 255, 255), font=font, align="center")
        img_path = output_path.replace(".mp4", "_fb.jpg")
        img.save(img_path, "JPEG", quality=95)
        self._ken_burns_effect(img_path, output_path, duration)
        os.remove(img_path)
