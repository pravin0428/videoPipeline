"""Video shot generation — provider-agnostic.

The renderer never knows where video came from.
All generation is delegated to the provider layer.
"""
import os
import time

from video_engine.errors import VideoGenerationError
from video_engine.models import Project
from video_engine.providers import ProviderManager, VideoAsset
from video_engine.utils.ffmpeg import get_duration
from video_engine.utils.logging import LOG
from video_engine.config import PROVIDER


def generate_all_shots(project: Project, output_dir: str, api_key: str = "") -> Project:
    LOG.info("Generating video shots...")
    shots_total = sum(len(s.shots) for s in project.scenes)
    shots_done = 0
    total_start = time.time()

    config = {
        "api_key": api_key,
        "resolution": project.resolution or "1080x1920",
        "fps": project.fps or 30,
    }
    manager = ProviderManager(primary=PROVIDER, config=config)
    manager.initialize()

    for scene in project.scenes:
        scene_dir = os.path.join(output_dir, "scenes", f"scene_{scene.scene_id}")
        os.makedirs(scene_dir, exist_ok=True)

        for j, shot in enumerate(scene.shots):
            out_path = os.path.join(scene_dir, f"shot_{j + 1:02d}.mp4")
            shots_done += 1
            shot_start = time.time()
            LOG.info(f"  [{shots_done}/{shots_total}] Scene {scene.scene_id}, shot {j + 1}: "
                     f"{shot.shot_type.value} — \"{shot.search_prompt}\" ({shot.duration_seconds:.1f}s)")

            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                actual = get_duration(out_path)
                if actual > 0 and abs(actual - shot.duration_seconds) < 1.5:
                    shot.video_path = out_path
                    LOG.info(f"    (cached)")
                    continue

            options = {
                "output_path": out_path,
                "duration": shot.duration_seconds,
                "shot_type": shot.shot_type.value if shot.shot_type else "",
                "fps": project.fps or 30,
                "resolution": project.resolution or "1080x1920",
                "shot_id": shot.shot_id,
                "negative_prompt": shot.negative_prompt,
            }

            asset: VideoAsset = manager.generate_clip(shot.search_prompt, options)

            if asset.local_path and os.path.exists(asset.local_path) and os.path.getsize(asset.local_path) > 1000:
                shot.video_path = asset.local_path
                elapsed = time.time() - shot_start
                LOG.info(f"    done in {elapsed:.1f}s (provider={asset.provider_name})")
            else:
                raise VideoGenerationError(
                    f"Failed to generate shot {j + 1} in scene {scene.scene_id} "
                    f"— provider '{manager.primary_name}' produced no output",
                    module="video_generator",
                    scene_id=scene.scene_id,
                    hint=f"Search prompt: \"{shot.search_prompt}\"",
                )

    total_elapsed = time.time() - total_start
    LOG.done(f"Generated {shots_total} shots in {total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")

    if manager.get_metrics():
        LOG.info("  Provider metrics:")
        for name, metrics in manager.get_metrics().items():
            gens = metrics.get("generations", 0)
            t = metrics.get("total_time", 0)
            status = metrics.get("status", "unknown")
            LOG.info(f"    {name}: status={status}, generations={gens}, time={t:.0f}s")

    return project
