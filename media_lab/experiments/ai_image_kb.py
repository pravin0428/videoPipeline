"""
Experiment 3: AI-Generated Image (Stable Diffusion) + Ken Burns Effect
Generates a still image from text using Stable Diffusion on MPS,
then applies slow pan/zoom via FFmpeg.
Requires: PyTorch, diffusers, transformers, Pillow
GPU memory estimate: ~2-3 GB for SD 2.1
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.base import Metrics, render_ken_burns


# Model choice: lighter models for M2 16GB
SD_MODEL = "runwayml/stable-diffusion-v1-5"  # ~2GB, very reliable on MPS
# SD_MODEL = "stabilityai/stable-diffusion-2-1"  # ~2.5GB, better quality


def run(scene: dict, output_dir: str) -> Metrics:
    m = Metrics()
    m.set("technique", "AI Image (SD 1.5) + Ken Burns")
    m.set("notes", {"model": SD_MODEL, "inference": "MPS (Apple Silicon)"})

    prompt = scene.get("ai_image_prompt", {}).get("positive", "temple at sunrise")
    negative = scene.get("ai_image_prompt", {}).get("negative", "blurry, low quality")
    duration = scene.get("duration_seconds", 5)
    resolution = scene.get("resolution", "1080x1920")
    target_w, target_h = resolution.split("x")

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "ai_image_kb.mp4")
    img_path = os.path.join(output_dir, "generated.png")

    try:
        # --- Generation Phase ---
        with m.timer("generation"):
            # Import inside timer to measure cold start
            import torch
            from diffusers import StableDiffusionPipeline

            # Load pipeline (may download on first run)
            pipe = StableDiffusionPipeline.from_pretrained(
                SD_MODEL,
                torch_dtype=torch.float32,  # MPS works best with float32
                safety_checker=None,
                requires_safety_checker=False,
                use_safetensors=True,
                variant="fp16",  # lighter
            )

            # Move to MPS
            start_load = time.time()
            pipe = pipe.to("mps")
            load_time = time.time() - start_load
            m.set("notes", {"model_load_time_s": round(load_time, 2)})

            # Enable attention slicing for memory efficiency
            pipe.enable_attention_slicing()

            # Generate image
            # Using SD 1.5 native 512x512 for speed on M2 MPS
            gen_start = time.time()
            result = pipe(
                prompt=prompt,
                negative_prompt=negative,
                width=512,
                height=512,
                num_inference_steps=15,
                guidance_scale=7.0,
            )
            gen_time = time.time() - gen_start
            m.set("notes", {"gen_time_s": round(gen_time, 2)})

            image = result.images[0]
            image.save(img_path)
            m.update_peak_memory()

            # Clean up to free memory
            del pipe
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

        # --- Render Phase (Ken Burns) ---
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
        # Try to save partial result if image was generated
        if os.path.exists(img_path):
            try:
                render_time = render_ken_burns(
                    img_path, out_path,
                    duration=duration,
                    resolution=resolution
                )
                m.data["render_time_s"] = render_time
                m.data["total_time_s"] = m.data.get("generation_time_s", 0) + render_time
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
    m = run(scene, os.path.join(output, "ai_image_kb"))
    print(m.summary())
    m.to_file(os.path.join(output, "ai_image_kb", "metrics.json"))
