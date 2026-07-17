"""Final video renderer: normalize → concat → mux audio + subtitles."""
import hashlib
import os
import subprocess
import time

from video_engine.errors import RenderError
from video_engine.models import Project
from video_engine.utils.ffmpeg import normalize_video, concat_videos, concat_audio, mux_audio_subtitles
from video_engine.utils.logging import LOG
from video_engine.config import CACHE_DIRS


def render(
    project: Project,
    shot_video_paths: list[str],
    tts_audio_paths: list[str],
    subtitle_path: str,
    output_path: str,
):
    LOG.info("Rendering final video...")
    render_start = time.time()

    work_dir = os.path.dirname(output_path)
    os.makedirs(work_dir, exist_ok=True)
    normalize_cache = CACHE_DIRS["normalized"]
    os.makedirs(normalize_cache, exist_ok=True)

    # Step 1: Normalize all shots with resume
    LOG.info("  Normalizing shots...")
    norm_start = time.time()
    normalized_paths: list[str] = []
    normalized_count = 0
    cached_count = 0
    for i, sv in enumerate(shot_video_paths):
        path_hash = hashlib.md5(sv.encode()).hexdigest()[:12]
        cache_key = f"{path_hash}_{os.path.basename(sv)}".replace(".mp4", f"_n_{project.fps}fps.mp4")
        norm_path = os.path.join(normalize_cache, cache_key)

        if os.path.exists(norm_path) and os.path.getsize(norm_path) > 1000:
            normalized_paths.append(norm_path)
            cached_count += 1
            continue

        dur = _get_shot_duration(project, i)
        ok = normalize_video(
            sv, norm_path, dur,
            target_fps=project.fps if project.fps else 30,
            resolution=project.resolution or "1080x1920",
        )
        if ok:
            normalized_paths.append(norm_path)
            normalized_count += 1
        else:
            LOG.warn(f"  Normalize failed for shot {i + 1}, using original")
            normalized_paths.append(sv)

    LOG.info(f"  Normalized {normalized_count} shots ({cached_count} cached) in {time.time() - norm_start:.0f}s")

    # Step 2: Concatenate videos
    LOG.info("  Concatenating shots...")
    concat_start = time.time()
    concat_video_path = os.path.join(work_dir, "_concat_video.mp4")
    ok = concat_videos(normalized_paths, concat_video_path)
    if not ok:
        LOG.warn("  Concat demuxer failed, retrying with filter_complex...")
        ok = _concat_filter_complex(normalized_paths, concat_video_path, project.fps or 30)
        if not ok:
            raise RenderError(
                "Failed to concatenate shot videos",
                module="renderer",
                hint="Check that all shots are valid MP4 files",
            )
    LOG.info(f"  Concatenated {len(normalized_paths)} shots in {time.time() - concat_start:.0f}s")

    # Step 3: Concatenate TTS audio
    LOG.info("  Concatenating audio...")
    audio_start = time.time()
    concat_audio_path = os.path.join(work_dir, "_concat_audio.mp3")
    ok = concat_audio(tts_audio_paths, concat_audio_path)
    if not ok:
        raise RenderError(
            "Failed to concatenate TTS audio files",
            module="renderer",
        )
    LOG.info(f"  Concatenated {len(tts_audio_paths)} audio files in {time.time() - audio_start:.0f}s")

    # Step 4: Mux everything together
    LOG.info("  Muxing video + audio + subtitles...")
    mux_start = time.time()
    ok = mux_audio_subtitles(
        concat_video_path, concat_audio_path, subtitle_path,
        output_path, volume_gain=6.0,
    )
    if not ok:
        raise RenderError(
            "Failed to mux final video",
            module="renderer",
            hint="Check FFmpeg output for details",
        )
    LOG.info(f"  Muxed in {time.time() - mux_start:.0f}s")

    final_size = os.path.getsize(output_path) / 1e6
    from video_engine.utils.ffmpeg import get_duration
    final_dur = get_duration(output_path)
    LOG.done(f"Final video: {output_path}")
    LOG.info(f"  Size: {final_size:.1f} MB, Duration: {final_dur:.1f}s, "
             f"Total render: {time.time() - render_start:.0f}s")

    LOG.info(f"  Cached normalized files kept at {normalize_cache} for resume")


def _get_shot_duration(project: Project, index: int) -> float:
    shot_idx = 0
    for scene in project.scenes:
        for shot in scene.shots:
            if shot_idx == index:
                return shot.duration_seconds
            shot_idx += 1
    return 5.0


def _concat_filter_complex(
    video_paths: list[str], output_path: str, fps: int
) -> bool:
    try:
        filter_parts = []
        for i in range(len(video_paths)):
            filter_parts.append(f"[{i}:v][{i}:a]")
        filter_str = "".join(filter_parts) + f"concat=n={len(video_paths)}:v=1:a=1[outv][outa]"
        input_args = []
        for vp in video_paths:
            input_args.extend(["-i", vp])
        result = subprocess.run(
            ["ffmpeg", "-y"] + input_args + [
                "-filter_complex", filter_str,
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                output_path,
            ],
            capture_output=True, text=True, timeout=600,
        )
        return result.returncode == 0
    except Exception:
        return False
