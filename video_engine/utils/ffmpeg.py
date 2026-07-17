"""FFmpeg/FFprobe utility functions."""
import json
import os
import subprocess
from pathlib import Path


def get_duration(filepath: str) -> float:
    """Get media duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath],
            capture_output=True, text=True, timeout=15,
        )
        info = json.loads(result.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def normalize_video(
    input_path: str,
    output_path: str,
    duration: float,
    target_fps: int = 30,
    resolution: str = "1080x1920",
    preset: str = "ultrafast",
    crf: int = 18,
) -> bool:
    """Re-encode a video to target FPS/resolution with silent audio track."""
    try:
        target_w, target_h = (int(x) for x in resolution.split("x"))
        scale_filter = (
            f"scale='max({target_w},iw*{target_h}/ih)':'max({target_h},ih*{target_w}/iw)',"
            f"crop={target_w}:{target_h}"
        )
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-f", "lavfi", "-t", str(max(duration, 1)), "-i", "anullsrc=r=48000:cl=mono",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(target_fps),
            "-vf", scale_filter,
            "-preset", preset, "-crf", str(crf),
            "-c:a", "aac", "-b:a", "32k",
            "-shortest",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0 and os.path.getsize(output_path) > 1000
    except Exception:
        return False


def _escape_concat_path(path: str) -> str:
    return path.replace("'", "'\\''")

def concat_videos(video_paths: list[str], output_path: str) -> bool:
    """Concatenate videos using concat demuxer. All inputs must have identical codecs/fps/resolution."""
    try:
        work_dir = os.path.dirname(output_path)
        concat_list = os.path.join(work_dir, "_concat_list.txt")
        with open(concat_list, "w") as f:
            for vp in video_paths:
                f.write(f"file '{_escape_concat_path(vp)}'\n")

        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_list, "-c", "copy", output_path],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return False
        return os.path.getsize(output_path) > 1000
    except Exception:
        return False


def concat_audio(audio_paths: list[str], output_path: str) -> bool:
    """Concatenate audio files using concat demuxer."""
    try:
        work_dir = os.path.dirname(output_path)
        list_path = os.path.join(work_dir, "_audio_list.txt")
        with open(list_path, "w") as f:
            for ap in audio_paths:
                f.write(f"file '{_escape_concat_path(ap)}'\n")

        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c", "copy", output_path],
            capture_output=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def mux_audio_subtitles(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_path: str,
    volume_gain: float = 6.0,
) -> bool:
    """Mux video + audio + subtitles into final MP4."""
    try:
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path, "-i", subtitle_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-c:s", "mov_text",
            "-metadata:s:s:0", "language=hin",
            "-af", f"volume={volume_gain}",
            "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0",
            "-shortest",
            output_path,
        ], capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            return False
        return os.path.getsize(output_path) > 1000
    except Exception:
        return False
