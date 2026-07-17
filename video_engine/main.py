#!/usr/bin/env python3
"""
Video Engine — AI Documentary Video Generator V2.1
===================================================
Deterministic pipeline: no LLM scene planning, no LLM prompt generation.
Loads a structured project JSON or a named script from the existing library,
then runs: validate → continuity fill → format prompts → TTS → video generation → subtitles → render.

Usage:
    python -m video_engine.main                      # interactive prompt
    python -m video_engine.main projects/ants/project.json
    python -m video_engine.main ants                  # named script from library
"""
import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_env():
    env_path = ROOT / "atlas" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def _get_api_key() -> str:
    _load_env()
    return os.environ.get("PEXELS_API_KEY", "")


# ── Step functions ──


def step_load_project(arg: str):
    from video_engine.project_loader import auto_detect_input
    return auto_detect_input(arg)


def step_validate(project):
    from video_engine.project_validator import validate_project
    return validate_project(project)


def step_continuity(project):
    from video_engine.continuity import ContinuityManager
    mgr = ContinuityManager(project)
    return mgr.auto_fill_continuity()


def step_format_prompts(project):
    from video_engine.prompt_formatter import format_all_prompts
    return format_all_prompts(project)


async def step_generate_tts(project, tts_dir: str):
    from video_engine.tts_generator import generate_all_tts
    return await generate_all_tts(project, tts_dir)


def fit_durations_to_narration(project, tail: float = 0.4, min_shot: float = 2.0):
    """Stretch each scene's shots so the footage covers its narration.

    Video length per shot is otherwise fixed at ``duration_seconds`` regardless of
    how long the spoken narration is. When narration is longer than the footage,
    the concatenated audio outlasts the video and the final mux (``-shortest``)
    clips the tail — cutting off the last words. Narration is the master clock for
    a documentary, so after TTS we size each scene's footage to its measured
    narration length (plus a small tail of silence).
    """
    for scene in project.scenes:
        if not scene.shots or scene.tts_duration <= 0:
            continue
        n = len(scene.shots)
        target = max(scene.tts_duration + tail, n * min_shot)
        per = round(target / n, 2)
        for shot in scene.shots:
            shot.duration_seconds = per
    return project


def step_generate_videos(project, shots_dir: str, api_key: str):
    from video_engine.video_generator import generate_all_shots
    return generate_all_shots(project, shots_dir, api_key=api_key)


def step_generate_subtitles(project, srt_path: str):
    from video_engine.subtitle_generator import generate_subtitles
    return generate_subtitles(project, srt_path)


def step_render(project, shot_paths, tts_paths, srt_path, output_path):
    from video_engine.renderer import render
    render(project, shot_paths, tts_paths, srt_path, output_path)


# ── Pipeline orchestration ──


def collect_shot_paths(project) -> list[str]:
    paths = []
    for scene in project.scenes:
        for shot in scene.shots:
            if shot.video_path and os.path.exists(shot.video_path):
                paths.append(shot.video_path)
    return paths


def _format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds:.0f}s ({seconds / 60:.1f}min)"


async def run_pipeline(arg: str):
    from video_engine.utils.logging import LOG

    pipeline_start = time.time()
    stage_timings: list[tuple[str, float]] = []
    total_steps = 7

    # Step 1: Load
    t0 = time.time()
    LOG.step(1, total_steps, "Load Project")
    project = step_load_project(arg)
    project = step_validate(project)
    scene_count = len(project.scenes)
    shot_count = sum(len(s.shots) for s in project.scenes)
    LOG.done(f"'{project.title}' — {scene_count} scenes, {shot_count} shots")
    stage_timings.append(("Load", time.time() - t0))

    # Step 2: Continuity
    t0 = time.time()
    LOG.step(2, total_steps, "Continuity Fill")
    project = step_continuity(project)
    LOG.done("Continuity defaults applied")
    stage_timings.append(("Continuity", time.time() - t0))

    # Step 3: Format Prompts
    t0 = time.time()
    LOG.step(3, total_steps, "Format Prompts")
    project = step_format_prompts(project)
    stage_timings.append(("Prompts", time.time() - t0))

    # Step 4: TTS
    t0 = time.time()
    LOG.step(4, total_steps, "Generate TTS")
    tts_dir = os.path.join(project.output_path, "tts")
    tts_paths = await step_generate_tts(project, tts_dir)
    # Size footage to the measured narration so nothing gets cut off at the end.
    project = fit_durations_to_narration(project)
    stage_timings.append(("TTS", time.time() - t0))

    # Step 5: Generate Videos
    t0 = time.time()
    LOG.step(5, total_steps, "Generate Videos")
    api_key = _get_api_key()
    if not api_key:
        LOG.warn("PEXELS_API_KEY not set. Videos will use fallback text scenes.")
    shots_dir = os.path.join(project.output_path, "scenes")
    project = step_generate_videos(project, shots_dir, api_key)
    shot_paths = collect_shot_paths(project)
    stage_timings.append(("Videos", time.time() - t0))

    # Step 6: Subtitles
    t0 = time.time()
    LOG.step(6, total_steps, "Generate Subtitles")
    srt_path = os.path.join(project.output_path, "subtitles.srt")
    step_generate_subtitles(project, srt_path)
    stage_timings.append(("Subtitles", time.time() - t0))

    # Step 7: Render
    t0 = time.time()
    LOG.step(7, total_steps, "Render Final Video")
    output_filename = f"{project.title}_documentary.mp4"
    output_path = os.path.join(project.output_path, output_filename)
    step_render(project, shot_paths, tts_paths, srt_path, output_path)
    stage_timings.append(("Render", time.time() - t0))

    total_elapsed = time.time() - pipeline_start
    LOG.info("")
    LOG.info(f"{'=' * 56}")
    LOG.info(f"  Pipeline Summary")
    LOG.info(f"{'=' * 56}")
    for name, dur in stage_timings:
        pct = (dur / total_elapsed) * 100
        LOG.info(f"  {name:<12s} {_format_elapsed(dur):>12s}  ({pct:5.1f}%)")
    LOG.info(f"  {'TOTAL':<12s} {_format_elapsed(total_elapsed):>12s}  (100%)")
    LOG.info(f"{'=' * 56}")
    LOG.info(f"Output: {output_path}")
    LOG.info(f"{'=' * 56}")


def main():
    from video_engine.utils.logging import LOG

    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        arg = input("Enter project path or script name: ").strip()
        if not arg:
            LOG.fail("No input provided.")
            sys.exit(1)

    try:
        asyncio.run(run_pipeline(arg))
    except Exception as e:
        LOG.fail(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
