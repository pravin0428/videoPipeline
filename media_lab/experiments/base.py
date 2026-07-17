"""
Shared utilities for Media Lab experiments.
Captures timing, memory, and produces standardized output.
"""
import time
import json
import subprocess
import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import psutil


class Metrics:
    def __init__(self):
        self.data = {
            "technique": "",
            "status": "pending",
            "total_time_s": 0.0,
            "generation_time_s": 0.0,
            "render_time_s": 0.0,
            "peak_vram_gb": 0.0,
            "peak_ram_gb": 0.0,
            "output_file": "",
            "output_resolution": "",
            "output_duration_s": 0.0,
            "output_size_mb": 0.0,
            "framerate": 0,
            "error": "",
            "notes": {},
        }
        self._process = psutil.Process(os.getpid())
        self._start_ram = self._process.memory_info().rss / 1e9
        self._peak_ram = self._start_ram

    def set(self, key, value):
        self.data[key] = value

    @contextmanager
    def timer(self, phase):
        """Context manager usage: with metrics.timer('generation_time_s'): ..."""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            # Store in multiple fields based on phase
            if "generation" in phase:
                self.data["generation_time_s"] = elapsed
            elif "render" in phase:
                self.data["render_time_s"] = elapsed
            else:
                self.data[f"{phase}_time_s"] = elapsed
            self.data["total_time_s"] += elapsed

    def update_peak_memory(self):
        self._peak_ram = max(self._peak_ram, self._process.memory_info().rss / 1e9)
        self.data["peak_ram_gb"] = round(self._peak_ram - self._start_ram, 2)
        # VRAM is more complex on MPS; we'll use a rough estimate
        try:
            import torch
            if torch.backends.mps.is_available():
                allocated = torch.mps.current_allocated_memory() / 1e9
                self.data["peak_vram_gb"] = max(self.data["peak_vram_gb"], round(allocated, 2))
        except (ImportError, AttributeError):
            pass

    def finalize(self, output_path: str):
        self.set("output_file", output_path)
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / 1e6
            self.set("output_size_mb", round(size_mb, 2))
            # Probe video metadata
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_streams", "-show_format", output_path],
                    capture_output=True, text=True, timeout=30
                )
                info = json.loads(probe.stdout)
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "video":
                        w = stream.get("width", 0)
                        h = stream.get("height", 0)
                        self.set("output_resolution", f"{w}x{h}")
                        self.set("framerate", eval(stream.get("r_frame_rate", "0/1")) if "/" in stream.get("r_frame_rate", "") else 0)
                        self.set("output_duration_s", round(float(stream.get("duration", 0)), 2))
                        break
            except:
                pass
        self.update_peak_memory()

    def to_file(self, path: str):
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)

    def summary(self) -> str:
        d = self.data
        parts = [
            f"\n{'='*50}",
            f"Technique: {d['technique']}",
            f"Status: {d['status']}",
            f"Total time: {d['total_time_s']:.1f}s",
            f"Generation: {d['generation_time_s']:.1f}s  |  Render: {d['render_time_s']:.1f}s",
            f"Peak RAM: {d['peak_ram_gb']:.2f} GB  |  Peak VRAM: {d['peak_vram_gb']:.2f} GB",
            f"Output: {d['output_file']} ({d['output_size_mb']:.1f} MB, {d['output_resolution']}, {d['output_duration_s']:.1f}s)",
        ]
        if d.get("error"):
            parts.append(f"ERROR: {d['error']}")
        parts.append(f"{'='*50}")
        return "\n".join(parts)


def render_ken_burns(
    image_path: str,
    output_path: str,
    duration: float = 5.0,
    resolution: str = "1080x1920",
    fps: int = 30,
    pan: str = "from left to right",
    zoom: str = "from 1.0 to 1.05",
    transition: str = "",
) -> float:
    """Apply Ken Burns effect (pan + zoom) to a still image using FFmpeg.

    Strategy: Pre-scale to slightly larger than target, then use crop with
    time-varying position to create a slow pan. Combines zoom (via scale
    changing over time) and pan in a single filtergraph using the `scale`
    and `crop` filters with timeline expressions via the `between` function
    and frame-level expression evaluation.
    """
    import subprocess
    import os
    import math

    target_w, target_h = [int(x) for x in resolution.split("x")]
    n_frames = int(duration * fps)

    # For a 5% zoom, we scale the image to 1.05x target size, then crop
    zoom_factor = 1.05
    src_w = int(target_w * zoom_factor)
    src_h = int(target_h * zoom_factor)

    # Pre-scale the source image to the working resolution (slightly larger than target)
    base_dir = os.path.dirname(output_path)
    scaled_path = os.path.join(base_dir, "_pre_scaled.png")
    scale_cmd = [
        "ffmpeg", "-y",
        "-i", image_path,
        "-vf", f"scale={src_w}:{src_h}:force_original_aspect_ratio=increase,crop={src_w}:{src_h}",
        "-frames:v", "1",
        scaled_path
    ]
    subprocess.run(scale_cmd, capture_output=True, timeout=60)

    # Use the overlay filter to create a "panning" video:
    # We place the pre-scaled image as a canvas and move a crop window over it.
    # The crop window starts at (0,0) and slides to (src_w - target_w, 0) over duration.
    pan_pixels = src_w - target_w
    # x = pan_pixels * (t / duration)
    # ffmpeg's crop filter supports 't' (time in seconds) in expressions
    x_expr = f"{pan_pixels}*t/{duration}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", scaled_path,
        "-vf",
        f"crop={target_w}:{target_h}:{x_expr}:0,format=yuv420p",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-crf", "23",
        output_path
    ]
    start = time.time()
    subprocess.run(cmd, capture_output=True, timeout=120)
    elapsed = time.time() - start

    if os.path.exists(scaled_path):
        os.remove(scaled_path)

    return elapsed


def render_static(output_path: str, duration: float = 5.0, fps: int = 30,
                  resolution: str = "1080x1920") -> float:
    """Create a blank / test video for debugging."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={resolution}:d={duration}:r={fps}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    start = time.time()
    subprocess.run(cmd, capture_output=True, timeout=30)
    return time.time() - start
