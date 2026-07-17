"""
Experiment 4: AI Image (SD) + Image-to-Video (Stable Video Diffusion)
Generates a still image via SD, then uses SVD to create a short video clip.
Frame interpolation via FFmpeg to reach target duration.
Requires: PyTorch, diffusers, transformers, Pillow
GPU memory estimate: ~4-5 GB for SD + SVD
"""
import os
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.base import Metrics


SD_MODEL = "runwayml/stable-diffusion-v1-5"
SVD_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"


def run(scene: dict, output_dir: str) -> Metrics:
    m = Metrics()
    m.set("technique", "AI Image (SD) + I2V (SVD)")
    m.set("notes", {"sd_model": SD_MODEL, "svd_model": SVD_MODEL})

    img_prompt = scene.get("ai_image_prompt", {}).get("positive", "temple at sunrise")
    img_negative = scene.get("ai_image_prompt", {}).get("negative", "blurry")
    duration = scene.get("duration_seconds", 5)
    resolution = scene.get("resolution", "1080x1920")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "ai_i2v.mp4")
    img_path = os.path.join(output_dir, "i2v_input.png")
    raw_video = os.path.join(output_dir, "svd_raw.mp4")

    try:
        import torch
        from diffusers import StableDiffusionPipeline, StableVideoDiffusionPipeline
        from PIL import Image
        import numpy as np

        with m.timer("generation"):
            # --- Step 1: Generate image via SD ---
            sd_pipe = StableDiffusionPipeline.from_pretrained(
                SD_MODEL,
                torch_dtype=torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
                use_safetensors=True,
                variant="fp16",
            )
            sd_pipe = sd_pipe.to("mps")
            sd_pipe.enable_attention_slicing()

            result = sd_pipe(
                prompt=img_prompt,
                negative_prompt=img_negative,
                width=768,
                height=768,
                num_inference_steps=25,
                guidance_scale=7.0,
            )
            image = result.images[0]
            image.save(img_path)
            m.update_peak_memory()

            # Free SD memory
            del sd_pipe
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

            # --- Step 2: Generate video via SVD ---
            svd_pipe = StableVideoDiffusionPipeline.from_pretrained(
                SVD_MODEL,
                torch_dtype=torch.float32,
                variant="fp16",
                use_safetensors=True,
            )
            svd_pipe = svd_pipe.to("mps")
            svd_pipe.enable_attention_slicing()

            # Resize image for SVD (expects 1024x576 or similar)
            svd_input = image.resize((1024, 576), Image.LANCZOS)

            gen_start = time.time()
            frames = svd_pipe(
                svd_input,
                decode_chunk_size=8,
                num_frames=25,
                motion_bucket_id=127,
                noise_aug_strength=0.02,
            ).frames[0]
            gen_time = time.time() - gen_start
            m.set("notes", {"svd_gen_time_s": round(gen_time, 2)})
            m.update_peak_memory()

            # Save frames as raw video
            frame_dir = os.path.join(output_dir, "svd_frames")
            os.makedirs(frame_dir, exist_ok=True)
            for i, frame in enumerate(frames):
                frame.save(os.path.join(frame_dir, f"frame_{i:04d}.png"))

            # Encode to video at 8fps (25 frames / ~3 seconds)
            cmd = [
                "ffmpeg", "-y",
                "-framerate", "8",
                "-i", os.path.join(frame_dir, "frame_%04d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "medium",
                "-crf", "18",
                raw_video,
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)

            # Free SVD memory
            del svd_pipe, frames
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

        # --- Render Phase: Interpolate to target duration + resolution ---
        with m.timer("render"):
            target_w, target_h = resolution.split("x")

            if os.path.exists(raw_video):
                # Get source fps and duration
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_streams", raw_video],
                    capture_output=True, text=True, timeout=15
                )
                import json
                info = json.loads(probe.stdout)
                src_fps = 8
                src_frames = 25
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "video":
                        rfr = stream.get("r_frame_rate", "8/1")
                        if "/" in rfr:
                            nums = rfr.split("/")
                            src_fps = float(nums[0]) / float(nums[1]) if float(nums[1]) > 0 else 8
                        src_frames = int(stream.get("nb_frames", 25))

                target_fps = 30
                target_frames = int(duration * target_fps)

                # Use minterpolate for smooth slow motion + frame interpolation
                # First resize/crop to target, then interpolate
                filter_chain = (
                    f"scale='max({target_w},iw*{target_h}/ih)':'max({target_h},ih*{target_w}/iw)',"
                    f"crop={target_w}:{target_h},"
                    f"setpts={src_frames/target_frames}*PTS,"
                    f"minterpolate=fps={target_fps}:mi_mode=mci:scd=none"
                )

                cmd = [
                    "ffmpeg", "-y",
                    "-i", raw_video,
                    "-vf", filter_chain,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-preset", "medium",
                    "-crf", "18",
                    out_path,
                ]
                subprocess.run(cmd, capture_output=True, timeout=300)
            else:
                raise Exception("SVD video not generated")

        m.set("status", "completed")
        m.finalize(out_path)

    except Exception as e:
        m.set("status", "failed")
        m.set("error", str(e))
        # If raw video exists, output that as partial
        if os.path.exists(raw_video):
            try:
                import shutil
                shutil.copy(raw_video, out_path)
                m.set("status", "partial")
                m.finalize(out_path)
            except:
                m.finalize("")
        else:
            m.finalize("")

    return m


if __name__ == "__main__":
    import yaml
    scene = yaml.safe_load(open(sys.argv[1]))["scene"]
    output = sys.argv[2] if len(sys.argv) > 2 else "output"
    m = run(scene, os.path.join(output, "ai_i2v"))
    print(m.summary())
    m.to_file(os.path.join(output, "ai_i2v", "metrics.json"))
