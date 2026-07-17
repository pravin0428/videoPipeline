"""
Experiment 5: Hybrid — Pexels Stock Video + AI-Generated Overlay
Downloads stock video from Pexels, generates an atmospheric overlay
(light leak / lens flare / particle effect) using AI image + compositing.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.base import Metrics


PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"


def run(scene: dict, output_dir: str) -> Metrics:
    m = Metrics()
    m.set("technique", "Hybrid: Pexels Video + AI Overlay")
    m.set("notes", {})

    query = scene.get("stock_search_queries", {}).get("pexels", "temple sunrise")
    duration = scene.get("duration_seconds", 5)
    resolution = scene.get("resolution", "1080x1920")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "hybrid.mp4")
    stock_path = os.path.join(output_dir, "stock.mp4")
    overlay_path = os.path.join(output_dir, "overlay.png")
    overlay_video = os.path.join(output_dir, "overlay.mp4")

    try:
        with m.timer("generation"):
            # --- Step 1: Download stock video from Pexels ---
            headers = {"Authorization": PEXELS_API_KEY}
            params = {
                "query": query,
                "per_page": 10,
                "orientation": "portrait",
                "size": "medium",
            }
            resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            videos = data.get("videos", [])

            if not videos:
                m.set("status", "failed")
                m.set("error", "No stock videos found")
                m.finalize("")
                return m

            # Pick best video
            best = None
            for v in videos:
                for file in v.get("video_files", []):
                    if file.get("width") and file.get("height"):
                        dur = v.get("duration", 0)
                        if dur >= duration * 0.8:
                            w, h = file["width"], file["height"]
                            if best is None or (w * h > best["area"]):
                                best = {"file": file, "area": w * h, "duration": dur, "id": v["id"]}

            if best is None:
                best = {"file": videos[0]["video_files"][0], "area": 0, "duration": 0, "id": videos[0]["id"]}

            dl_resp = requests.get(best["file"]["link"], timeout=60)
            dl_resp.raise_for_status()
            with open(stock_path, "wb") as f:
                f.write(dl_resp.content)

            m.set("notes", {"pexels_video_id": best["id"], "stock_source": "pexels"})

            # --- Step 2: Generate cinematic overlay using AI ---
            try:
                import torch
                from diffusers import StableDiffusionPipeline
                from PIL import Image

                overlay_pipe = StableDiffusionPipeline.from_pretrained(
                    "runwayml/stable-diffusion-v1-5",
                    torch_dtype=torch.float32,
                    safety_checker=None,
                    requires_safety_checker=False,
                    use_safetensors=True,
                    variant="fp16",
                )
                overlay_pipe = overlay_pipe.to("mps")
                overlay_pipe.enable_attention_slicing()

                # Generate a warm light leak / atmospheric overlay
                overlay_result = overlay_pipe(
                    prompt="cinematic golden light leak, warm bokeh, lens flare, atmospheric haze, 4K, black background with warm orange and gold light particles",
                    negative_prompt="sharp edges, text, faces, objects, buildings, cold colors, dark",
                    width=512,
                    height=512,
                    num_inference_steps=20,
                    guidance_scale=7.0,
                )
                overlay_img = overlay_result.images[0]
                overlay_img.save(overlay_path)

                del overlay_pipe
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

                m.set("notes", {"overlay_generated": True})

                # Convert overlay to video (slight pulsing effect)
                target_w, target_h = resolution.split("x")
                n_frames = int(duration * 30)

                # Create overlay video with subtle opacity animation
                filter_chain = (
                    f"format=rgba,"
                    f"scale={target_w}:{target_h},"
                    f"loop=loop={n_frames}:size=1:start=0,"
                    f"fade=t=in:st=0:d=0.5:alpha=1,"
                    f"fade=t=out:st={duration-0.5}:d=0.5:alpha=1"
                )
                cmd = [
                    "ffmpeg", "-y",
                    "-i", overlay_path,
                    "-vf", filter_chain,
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-pix_fmt", "yuva420p",
                    "-preset", "ultrafast",
                    overlay_video,
                ]
                subprocess.run(cmd, capture_output=True, timeout=60)

            except Exception as e:
                m.set("notes", {"overlay_error": str(e), "overlay_generated": False})
                # Proceed without overlay (stock-only)
                pass

            m.update_peak_memory()

        # --- Render Phase: Composite stock + overlay ---
        with m.timer("render"):
            target_w, target_h = resolution.split("x")

            # Get stock video duration
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", stock_path],
                capture_output=True, text=True, timeout=15
            )
            import json
            info = json.loads(probe.stdout)
            src_dur = 0
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    src_dur = float(stream.get("duration", 0))
                    break
            trim_dur = min(duration, src_dur)

            if os.path.exists(overlay_video) and os.path.getsize(overlay_video) > 1000:
                # Composite: stock video with overlay on top (screen blend + opacity)
                filter_complex = (
                    f"[0:v]scale={target_w}:{target_h}:force_original_aspect_ratio=1,"
                    f"crop={target_w}:{target_h}[bg];"
                    f"[1:v]format=rgba[ov];"
                    f"[bg][ov]overlay=(W-w)/2:(H-h)/2:format=auto,"
                    f"format=yuv420p[out]"
                )
                cmd = [
                    "ffmpeg", "-y",
                    "-i", stock_path,
                    "-i", overlay_video,
                    "-t", str(trim_dur),
                    "-filter_complex", filter_complex,
                    "-map", "[out]",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "18",
                    out_path,
                ]
            else:
                # No overlay: just trim + scale stock video
                filter_chain = (
                    f"scale='max({target_w},iw*{target_h}/ih)':'max({target_h},ih*{target_w}/iw)',"
                    f"crop={target_w}:{target_h}"
                )
                cmd = [
                    "ffmpeg", "-y",
                    "-i", stock_path,
                    "-t", str(trim_dur),
                    "-vf", filter_chain,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "18",
                    out_path,
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
    m = run(scene, os.path.join(output, "hybrid"))
    print(m.summary())
    m.to_file(os.path.join(output, "hybrid", "metrics.json"))
