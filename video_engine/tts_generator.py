"""Text-to-speech generation using edge-tts."""
import asyncio
import os

from video_engine.errors import TTSGenerationError
from video_engine.models import Project, Scene
from video_engine.utils.ffmpeg import get_duration
from video_engine.utils.logging import LOG


async def generate_scene_tts(scene: Scene, output_path: str, voice: str) -> float:
    text = scene.narration
    if not text:
        raise TTSGenerationError(
            f"Scene {scene.scene_id} has no narration text",
            module="tts", scene_id=scene.scene_id,
        )

    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text, voice=voice, rate="+0%", pitch="+0Hz",
        )
        await communicate.save(output_path)
    except Exception as e:
        raise TTSGenerationError(
            f"TTS failed: {e}",
            module="tts", scene_id=scene.scene_id,
            hint="Check voice name and internet connection",
        )

    dur = get_duration(output_path)
    if dur <= 0:
        raise TTSGenerationError(
            f"TTS produced empty audio",
            module="tts", scene_id=scene.scene_id,
        )

    scene.tts_duration = dur
    LOG.done(f"Scene {scene.scene_id}: TTS {os.path.basename(output_path)} ({dur:.1f}s)")
    return dur


async def generate_all_tts(project: Project, output_dir: str) -> list[str]:
    LOG.info("Generating TTS audio...")
    os.makedirs(output_dir, exist_ok=True)

    paths: list[str] = []
    tasks = []
    for scene in project.scenes:
        out_path = os.path.join(output_dir, f"scene_{scene.scene_id}.mp3")
        paths.append(out_path)
        tasks.append(generate_scene_tts(scene, out_path, project.voice))

    await asyncio.gather(*tasks)
    LOG.done(f"TTS generated for {len(project.scenes)} scenes")
    return paths
