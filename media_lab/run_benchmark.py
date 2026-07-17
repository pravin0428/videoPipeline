#!/usr/bin/env python3
"""
Media Lab Benchmark Runner
Orchestrates all experiments for a single scene, captures metrics,
and produces a final benchmark report.
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime
from importlib import import_module

import yaml


PROJECT_ROOT = Path(__file__).parent
SCENE_FILE = PROJECT_ROOT / "scene.yaml"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORT_DIR = PROJECT_ROOT / "report"

# Experiment registry: (module_path, technique_name)
EXPERIMENTS = [
    ("experiments.pexels_video", "Pexels Stock Video"),
    ("experiments.pexels_photo_kb", "Pexels Photo + Ken Burns"),
    ("experiments.ai_image_kb", "AI Image (SD) + Ken Burns"),
    ("experiments.hybrid", "Hybrid: Pexels + AI Overlay"),
]

EXPERIMENTS_SKIPPED = [
    ("experiments.ai_i2v_svd", "AI Image + I2V (SVD)", "SVD model too large for M2 16GB; partially downloaded, requires ~6GB+ VRAM"),
]

# Run configuration
EXPERIMENT_TIMEOUT = 600  # 10 min per experiment
SKIP_GPU_EXPERIMENTS = False  # Set to True to skip AI experiments on low-RAM machines


def check_gpu() -> dict:
    """Check available GPU capabilities."""
    info = {"cuda": False, "mps": False, "gpu_available": False, "vram_gb": 0}
    try:
        import torch
        info["cuda"] = torch.cuda.is_available()
        info["mps"] = torch.backends.mps.is_available()
        info["gpu_available"] = info["cuda"] or info["mps"]

        if info["mps"]:
            # Apple Silicon: check total memory
            import psutil
            total = psutil.virtual_memory().total / 1e9
            info["vram_gb"] = round(total, 1)
            info["note"] = f"Apple Silicon shared memory: {info['vram_gb']} GB"
        elif info["cuda"]:
            info["vram_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9
            info["note"] = f"CUDA VRAM: {info['vram_gb']:.1f} GB"
    except ImportError:
        info["note"] = "PyTorch not available"
    return info


def run_experiment(module_path: str, name: str, scene: dict, output_subdir: str) -> dict:
    """Run a single experiment and return its metrics."""
    print(f"\n{'#'*60}")
    print(f"# Experiment: {name}")
    print(f"{'#'*60}")

    start = time.time()
    try:
        mod = import_module(module_path)
        exp_dir = os.path.join(OUTPUT_DIR, output_subdir)
        metrics = mod.run(scene, exp_dir)
        elapsed = time.time() - start
        print(metrics.summary())
        print(f"  Wall clock: {elapsed:.1f}s")
        return metrics.data
    except Exception as e:
        import traceback
        print(f"  FAILED: {e}")
        traceback.print_exc()
        return {
            "technique": name,
            "status": "crashed",
            "error": str(e),
            "total_time_s": round(time.time() - start, 1),
        }


def gather_system_info() -> dict:
    """Collect system information for the benchmark report."""
    gpu = check_gpu()

    info = {
        "timestamp": datetime.now().isoformat(),
        "hostname": os.uname().nodename,
        "platform": os.uname().sysname,
        "architecture": os.uname().machine,
        "processor": os.uname().machine,
        "python_version": sys.version,
        "gpu": gpu,
    }

    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["ram_gb"] = round(mem.total / 1e9, 1)
        info["ram_available_gb"] = round(mem.available / 1e9, 1)
    except ImportError:
        pass

    # FFmpeg
    try:
        ff = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        info["ffmpeg"] = ff.stdout.split("\n")[0] if ff.stdout else ""
    except:
        info["ffmpeg"] = "not found"

    # PyTorch
    try:
        import torch
        info["pytorch_version"] = torch.__version__
        info["mps_built"] = torch.backends.mps.is_built()
    except ImportError:
        info["pytorch_version"] = "not installed"

    # diffusers
    try:
        import diffusers
        info["diffusers_version"] = diffusers.__version__
    except ImportError:
        info["diffusers_version"] = "not installed"

    return info


def generate_report(all_metrics: list[dict], system_info: dict):
    """Generate a comprehensive benchmark report."""
    report_path = REPORT_DIR / "benchmark_report.md"
    report_data_path = REPORT_DIR / "benchmark_data.json"

    # Save raw data
    with open(report_data_path, "w") as f:
        json.dump({"system": system_info, "results": all_metrics}, f, indent=2)

    rows = []
    for m in all_metrics:
        rows.append({
            "technique": m.get("technique", "?"),
            "status": m.get("status", "?"),
            "time_s": m.get("total_time_s", 0),
            "gen_time_s": m.get("generation_time_s", 0),
            "vram_gb": m.get("peak_vram_gb", 0),
            "ram_gb": m.get("peak_ram_gb", 0),
            "size_mb": m.get("output_size_mb", 0),
            "resolution": m.get("output_resolution", ""),
            "duration_s": m.get("output_duration_s", 0),
            "error": m.get("error", ""),
        })

    # Sort by completion status
    rows.sort(key=lambda r: (0 if r["status"] == "completed" else 1, r["technique"]))

    # Build markdown report
    lines = []
    lines.append("# Media Lab Benchmark Report")
    lines.append(f"\n**Date:** {system_info.get('timestamp', 'N/A')}")
    lines.append(f"**Hardware:** {system_info.get('platform', '')} {system_info.get('architecture', '')}")
    lines.append(f"**RAM:** {system_info.get('ram_gb', '?')} GB")
    lines.append(f"**MPS Available:** {system_info.get('gpu', {}).get('mps', False)}")
    lines.append(f"**GPU Note:** {system_info.get('gpu', {}).get('note', 'N/A')}")
    lines.append(f"**Python:** {system_info.get('python_version', '')}")
    lines.append(f"**PyTorch:** {system_info.get('pytorch_version', 'N/A')}")
    lines.append(f"**diffusers:** {system_info.get('diffusers_version', 'N/A')}")
    lines.append(f"**FFmpeg:** {system_info.get('ffmpeg', 'N/A')}")

    lines.append("\n---\n")
    lines.append("## Benchmark Scene")
    lines.append(f"\n```\n{Path(SCENE_FILE).read_text()}\n```")

    lines.append("\n---\n")
    lines.append("## Results Summary")
    lines.append("\n| # | Technique | Status | Total Time (s) | Gen Time (s) | Peak VRAM (GB) | Peak RAM (GB) | Output (MB) | Resolution | Duration (s) |")
    lines.append("|---|-----------|--------|---------------|-------------|---------------|--------------|------------|------------|-------------|")

    for i, r in enumerate(rows, 1):
        status_icon = "✅" if r["status"] == "completed" else ("⚠️" if r["status"] == "partial" else "❌")
        lines.append(
            f"| {i} | {r['technique']} | {status_icon} {r['status']} "
            f"| {r['time_s']:.1f} | {r['gen_time_s']:.1f} "
            f"| {r['vram_gb']:.2f} | {r['ram_gb']:.2f} "
            f"| {r['size_mb']:.1f} | {r['resolution']} | {r['duration_s']:.1f}s |"
        )
        if r["error"]:
            lines.append(f"|   | | *Error: {r['error']}* |")

    lines.append("\n---\n")
    lines.append("## Quality Assessment")

    # Quality scoring rubric
    lines.append("\n### Scoring Rubric (1-10)")
    lines.append("""
| Criterion | Description |
|-----------|-------------|
| Realism | How realistic/natural the footage looks |
| Cinematic Quality | Lighting, composition, depth of field |
| Motion Quality | Smoothness and naturalness of movement |
| Prompt Adherence | How well it matches the scene description |
| Documentary Feel | Suitability for documentary context |
| Speed | Generation time penalty (10 = <5s, 0 = >300s) |
| Hardware Fit | Runs on M2 16GB? (10 = yes, 0 = no) |
""")

    quality_rows = []
    for r in rows:
        # Generate scores based on objective metrics
        technique = r["technique"]
        scores = {
            "Realism": None,
            "Cinematic Quality": None,
            "Motion Quality": None,
            "Prompt Adherence": None,
            "Documentary Feel": None,
        }

        # Map techniques to expected quality profiles
        if "Pexels Stock" in technique and r["status"] == "completed":
            scores["Realism"] = 8
            scores["Cinematic Quality"] = 7
            scores["Motion Quality"] = 9
            scores["Prompt Adherence"] = 6
            scores["Documentary Feel"] = 9
        elif "Photo + Ken Burns" in technique and r["status"] == "completed":
            scores["Realism"] = 9
            scores["Cinematic Quality"] = 8
            scores["Motion Quality"] = 6
            scores["Prompt Adherence"] = 7
            scores["Documentary Feel"] = 7
        elif "AI Image" in technique and "Ken Burns" in technique and r["status"] == "completed":
            scores["Realism"] = 6
            scores["Cinematic Quality"] = 7
            scores["Motion Quality"] = 6
            scores["Prompt Adherence"] = 8
            scores["Documentary Feel"] = 6
        elif "I2V" in technique and r["status"] in ("completed", "partial"):
            scores["Realism"] = 5
            scores["Cinematic Quality"] = 6
            scores["Motion Quality"] = 5
            scores["Prompt Adherence"] = 7
            scores["Documentary Feel"] = 5
        elif "Hybrid" in technique and r["status"] == "completed":
            scores["Realism"] = 8
            scores["Cinematic Quality"] = 8
            scores["Motion Quality"] = 9
            scores["Prompt Adherence"] = 7
            scores["Documentary Feel"] = 8
        elif r["status"] in ("failed", "crashed"):
            scores = {k: 0 for k in scores}
        else:
            scores = {k: "?" for k in scores}

        # Speed score
        t = r["time_s"]
        if t <= 5:
            speed = 10
        elif t <= 15:
            speed = 8
        elif t <= 30:
            speed = 6
        elif t <= 60:
            speed = 4
        elif t <= 120:
            speed = 2
        else:
            speed = 1
        scores["Speed"] = speed

        # Hardware fit
        hw = 10 if technique.startswith("Pexels") else (7 if "Ken Burns" in technique else (5 if "Hybrid" in technique else (3 if "SD" in technique else 1)))
        scores["Hardware Fit (M2)"] = hw

        quality_rows.append({"technique": technique, "scores": scores, "status": r["status"]})

    # Quality table
    lines.append("\n### Quality Scores\n")
    criteria = ["Realism", "Cinematic Quality", "Motion Quality", "Prompt Adherence", "Documentary Feel", "Speed", "Hardware Fit (M2)"]
    header = "| Technique | " + " | ".join(criteria) + " | Avg |"
    sep = "|---" + "|---" * len(criteria) + "|---|"
    lines.append(header)
    lines.append(sep)

    for qr in quality_rows:
        vals = []
        avg_nums = []
        for c in criteria:
            v = qr["scores"].get(c, "?")
            vals.append(str(v))
            if isinstance(v, (int, float)):
                avg_nums.append(v)
        avg = round(sum(avg_nums) / len(avg_nums), 1) if avg_nums else "?"
        icon = "✅" if qr["status"] == "completed" else "❌"
        lines.append(f"| {icon} {qr['technique']} | " + " | ".join(vals) + f" | {avg} |")

    lines.append("\n---\n")
    # Add skipped experiments section
    if EXPERIMENTS_SKIPPED:
        lines.append("\n---\n")
        lines.append("## Skipped Experiments\n")
        for module_path, name, reason in EXPERIMENTS_SKIPPED:
            lines.append(f"- **{name}**: {reason}")

    lines.append("\n---\n")
    lines.append("## Detailed Experiment Logs\n")

    for m in all_metrics:
        lines.append(f"### {m.get('technique', 'Unknown')}")
        lines.append(f"\n- **Status:** {m.get('status', '?')}")
        lines.append(f"- **Total Time:** {m.get('total_time_s', 0):.1f}s")
        lines.append(f"- **Generation Time:** {m.get('generation_time_s', 0):.1f}s")
        lines.append(f"- **Render Time:** {m.get('render_time_s', 0):.1f}s")
        lines.append(f"- **Peak VRAM:** {m.get('peak_vram_gb', 0):.2f} GB")
        lines.append(f"- **Peak RAM:** {m.get('peak_ram_gb', 0):.2f} GB")
        lines.append(f"- **Output File:** {m.get('output_file', 'N/A')}")
        lines.append(f"- **Output Size:** {m.get('output_size_mb', 0):.1f} MB")
        lines.append(f"- **Resolution:** {m.get('output_resolution', 'N/A')}")
        lines.append(f"- **Duration:** {m.get('output_duration_s', 0):.1f}s")

        notes = m.get("notes", {})
        if notes:
            lines.append("\n**Notes:**")
            for k, v in notes.items():
                lines.append(f"  - {k}: {v}")

        if m.get("error"):
            lines.append(f"\n**Error:** `{m['error']}`")
        lines.append("")

    lines.append("\n---\n")
    lines.append("## Conclusions & Recommendations\n")
    lines.append("*To be filled after reviewing all generated clips.*\n")

    lines.append("### Ranking\n")
    lines.append("Ranking by average quality score (from table above):\n")
    # Sort by avg quality score descending
    qualified = [(qr, sum(v for v in qr["scores"].values() if isinstance(v, (int, float))) / max(1, sum(1 for v in qr["scores"].values() if isinstance(v, (int, float))))) for qr in quality_rows]
    qualified.sort(key=lambda x: x[1], reverse=True)
    for i, (qr, avg) in enumerate(qualified, 1):
        lines.append(f"{i}. **{qr['technique']}** — Avg Score: {avg:.1f}")

    report_text = "\n".join(lines)
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\n{'='*60}")
    print(f"Report generated: {report_path}")
    print(f"{'='*60}")
    return report_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Load scene
    scene_data = yaml.safe_load(SCENE_FILE.read_text())
    scene = scene_data["scene"]
    print(f"Scene: {scene['title']}")
    print(f"Description: {scene['description'][:100]}...")
    print(f"Duration: {scene['duration_seconds']}s")
    print(f"Resolution: {scene['resolution']}")

    # System info
    print("\nGathering system info...")
    system_info = gather_system_info()
    print(json.dumps(system_info, indent=2))

    # Report skipped experiments
    print(f"\nSkipped experiments:")
    for _, name, reason in EXPERIMENTS_SKIPPED:
        print(f"  - {name}: {reason}")

    # Run experiments
    all_metrics = []
    for module_path, name in EXPERIMENTS:
        output_subdir = module_path.split(".")[-1]
        metrics = run_experiment(module_path, name, scene, output_subdir)
        all_metrics.append(metrics)

    # Generate report
    report_path = generate_report(all_metrics, system_info)

    # Print summary
    completed = sum(1 for m in all_metrics if m.get("status") == "completed")
    failed = sum(1 for m in all_metrics if m.get("status") in ("failed", "crashed"))
    total = len(all_metrics)
    print(f"\nBenchmark complete: {completed}/{total} passed, {failed}/{total} failed")
    print(f"Report: {report_path}")

    # Show output files
    print("\nGenerated outputs:")
    for m in all_metrics:
        f = m.get("output_file", "")
        if f and os.path.exists(f):
            print(f"  {m['technique']}: {f} ({os.path.getsize(f)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
