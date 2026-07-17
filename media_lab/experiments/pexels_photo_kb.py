"""
Experiment 2: Pexels Stock Photo + Ken Burns Effect
Downloads a high-res still photo from Pexels, applies slow pan/zoom via FFmpeg.
No GPU needed.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.base import Metrics, render_ken_burns


API_KEY = os.environ.get("PEXELS_API_KEY", "")
PHOTO_URL = "https://api.pexels.com/v1/search"


def run(scene: dict, output_dir: str) -> Metrics:
    m = Metrics()
    m.set("technique", "Pexels Photo + Ken Burns")
    m.set("notes", {"source": "pexels.com/photos", "model": "N/A (API + FFmpeg)"})

    query = scene.get("stock_search_queries", {}).get("pexels", "temple sunrise")
    duration = scene.get("duration_seconds", 5)
    resolution = scene.get("resolution", "1080x1920")

    try:
        # Search photos
        with m.timer("generation"):
            headers = {"Authorization": API_KEY}
            params = {"query": query, "per_page": 15, "orientation": "portrait"}
            resp = requests.get(PHOTO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            photos = data.get("photos", [])
            if not photos:
                m.set("status", "failed")
                m.set("error", "No photos found")
                m.finalize("")
                return m

            # Pick largest photo
            best = max(photos, key=lambda p: p.get("width", 0) * p.get("height", 0))
            photo_url = best["src"]["original"]
            m.set("notes", {
                "query": query,
                "pexels_photo_id": best["id"],
                "photographer": best.get("photographer", ""),
                "source_url": photo_url,
            })
            m.update_peak_memory()

        # Download photo
        os.makedirs(output_dir, exist_ok=True)
        img_path = os.path.join(output_dir, "photo.jpg")
        img_resp = requests.get(photo_url, timeout=60)
        img_resp.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(img_resp.content)

        # Render Ken Burns
        out_path = os.path.join(output_dir, "photo_kb.mp4")
        render_time = render_ken_burns(
            img_path, out_path,
            duration=duration,
            resolution=resolution,
            fps=30,
            pan="from left to right",
            zoom="from 1.0 to 1.05",
        )
        m.data["render_time_s"] = render_time
        m.data["total_time_s"] = m.data.get("generation_time_s", 0) + render_time

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
    m = run(scene, os.path.join(output, "pexels_photo_kb"))
    print(m.summary())
    m.to_file(os.path.join(output, "pexels_photo_kb", "metrics.json"))
