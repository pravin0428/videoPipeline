"""
Experiment 1: Pexels Stock Video
Downloads matching stock video from Pexels API.
No GPU needed, purely network + disk.
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.base import Metrics


API_KEY = os.environ.get("PEXELS_API_KEY", "")
API_URL = "https://api.pexels.com/videos/search"


def run(scene: dict, output_dir: str) -> Metrics:
    m = Metrics()
    m.set("technique", "Pexels Stock Video")
    m.set("notes", {"source": "pexels.com", "model": "N/A (API-based)"})

    query = scene.get("stock_search_queries", {}).get("pexels", "temple sunrise")
    duration_target = scene.get("duration_seconds", 5)
    resolution = scene.get("resolution", "1080x1920")

    m.set("notes", {"query": query})

    try:
        # Search for videos
        with m.timer("generation"):
            headers = {"Authorization": API_KEY}
            params = {
                "query": query,
                "per_page": 15,
                "orientation": "portrait",
                "size": "medium",
            }
            resp = requests.get(API_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            videos = data.get("videos", [])
            if not videos:
                m.set("status", "failed")
                m.set("error", "No videos found from Pexels")
                m.finalize("")
                return m

            # Pick the best match: prefer videos >= duration_target, highest resolution
            best = None
            for v in videos:
                for file in v.get("video_files", []):
                    if file.get("width") and file.get("height"):
                        w, h = file["width"], file["height"]
                        dur = v.get("duration", 0)
                        if dur >= duration_target * 0.8:
                            if best is None or (w * h > best["area"]):
                                best = {
                                    "video": v,
                                    "file": file,
                                    "area": w * h,
                                    "duration": dur,
                                }

            if best is None:
                # Fallback: pick the longest available
                for v in videos:
                    for file in v.get("video_files", []):
                        dur = v.get("duration", 0)
                        if best is None or dur > best["duration"]:
                            best = {
                                "video": v,
                                "file": file,
                                "area": 0,
                                "duration": dur,
                            }

            video_url = best["file"]["link"]
            m.set("notes", {
                "query": query,
                "pexels_video_id": best["video"]["id"],
                "matched_duration": best["duration"],
                "source_url": video_url,
            })
            m.update_peak_memory()

        # Download
        os.makedirs(output_dir, exist_ok=True)
        dl_path = os.path.join(output_dir, "pexels_download.mp4")
        with m.timer("render"):
            dl_resp = requests.get(video_url, timeout=60)
            dl_resp.raise_for_status()
            with open(dl_path, "wb") as f:
                f.write(dl_resp.content)

            # Trim/crop to exact duration and resolution
            out_path = os.path.join(output_dir, "pexels_final.mp4")
            target_w, target_h = resolution.split("x")

            # First get source info
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", dl_path],
                capture_output=True, text=True, timeout=15
            )
            info = json.loads(probe.stdout)
            src_w, src_h = 0, 0
            src_dur = 0
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    src_w = stream.get("width", 0)
                    src_h = stream.get("height", 0)
                    src_dur = float(stream.get("duration", 0))
                    break

            # Build filter: scale to cover target, then crop center
            scale_filter = (
                f"scale='max({target_w},iw*{target_h}/ih)':"
                f"'max({target_h},ih*{target_w}/iw)',"
                f"crop={target_w}:{target_h}"
            )

            trim_duration = min(duration_target, src_dur)
            cmd = [
                "ffmpeg", "-y",
                "-i", dl_path,
                "-t", str(trim_duration),
                "-vf", scale_filter,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "18",
                out_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)

        m.set("status", "completed")
        m.finalize(out_path)

    except Exception as e:
        m.set("status", "failed")
        m.set("error", str(e))
        m.finalize("")

    return m


if __name__ == "__main__":
    import yaml
    scene = yaml.safe_load(open(sys.argv[1]))["scene"]
    output = sys.argv[2] if len(sys.argv) > 2 else "output"
    m = run(scene, os.path.join(output, "pexels"))
    print(m.summary())
    m.to_file(os.path.join(output, "pexels", "metrics.json"))
