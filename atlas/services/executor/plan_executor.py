"""PlanExecutor — dumb executor that reads a ProductionPlan and renders video.

The executor makes NO creative decisions.
It follows the plan exactly as written by the DirectorService.
Media providers are pluggable — any model can be swapped in.
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.config import settings
from core.logging import get_logger
from services.director_v5.models import ProductionPlan, ShotPlan
from services.media.providers.base import MediaAsset, MediaPlan
from services.media.providers.stock_video import StockVideoProvider
from services.media.providers.photo import PhotoProvider
from services.media.providers.map import MapProvider
from services.media.providers.infographic import InfographicProvider
from services.media.providers.animation import ScientificAnimationProvider
from services.renderer.documentary import DocumentaryRenderer
from services.scene.director import VisualStorytelling

logger = get_logger()


class PlanExecutor:
    def __init__(self, output_root: str | None = None):
        self.output_root = Path(output_root) if output_root else Path(settings.app_data_dir) / "executor"
        self.renderer = DocumentaryRenderer()
        self._providers: dict = {}

    async def execute(self, plan: ProductionPlan | dict | str, uid: str | None = None) -> dict:
        if isinstance(plan, str):
            with open(plan) as f:
                data = json.load(f)
            plan = self._dict_to_plan(data)
        elif isinstance(plan, dict):
            plan = self._dict_to_plan(plan)

        uid = uid or Path(tempfile.mktemp()).stem
        dirs = self._setup_dirs(uid)

        scene_videos = []
        scene_metadata = []
        all_assets = []

        for scene in plan.scenes:
            shot_videos = []
            for shot in scene.shots:
                assets = await self._resolve_media(shot, scene, dirs["media"])
                all_assets.extend(assets)

                if not assets:
                    assets = [MediaAsset(
                        media_type="stock_video",
                        file_path="",
                        duration=shot.duration,
                    )]

                for asset in assets:
                    shot_dir = dirs["scenes"] / f"scene_{scene.scene_number:04d}_shot_{shot.shot_number:04d}"
                    shot_dir.mkdir(parents=True, exist_ok=True)
                    output_path = str(shot_dir / "frame.mp4")

                    story = self._shot_to_storytelling(shot, scene)

                    shot_plan = MediaPlan(
                        scene_number=scene.scene_number,
                        media_type=asset.media_type,
                        narrative_context=scene.narrative,
                        duration=shot.duration,
                    )

                    self.renderer.render_scene([asset], shot_plan, story, output_path)
                    shot_videos.append(output_path)
                    logger.debug("shot_rendered", scene=scene.scene_number, shot=shot.shot_number, path=output_path)

            if shot_videos:
                concat_path = str(dirs["scenes"] / f"scene_{scene.scene_number:04d}_combined.mp4")
                self._concat_clips(shot_videos, concat_path)
                scene_videos.append(concat_path)

            scene_metadata.append({
                "scene": scene.scene_number,
                "narrative": scene.narrative[:50],
                "emotion": scene.emotion,
                "shots": len(scene.shots),
                "media_type": scene.recommended_media_type,
            })

        audio_path = await self._generate_audio(plan, uid)
        srt_path = self._generate_subtitles(plan, uid, audio_path)
        output_path = str(dirs["final"] / "final_v5.mp4")

        if scene_videos:
            final_path = self._concat_and_mux(scene_videos, audio_path, srt_path, output_path)
        else:
            final_path = ""

        return {
            "video_path": final_path,
            "uid": uid,
            "scenes": scene_metadata,
        }

    def _setup_dirs(self, uid: str) -> dict:
        d = {k: self.output_root.expanduser().resolve() / uid / k
             for k in ("media", "scenes", "audio", "final", "debug")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    async def _resolve_media(self, shot: ShotPlan, scene, media_dir: Path) -> list[MediaAsset]:
        priority = shot.media_priority if shot.media_priority else ["stock_video"]
        prompt = shot.cinematic_prompt or scene.stock_video_prompt or "documentary footage"

        for media_type in priority:
            provider = self._get_provider(media_type)
            if not provider:
                continue
            plan = MediaPlan(
                scene_number=scene.scene_number,
                media_type=media_type,
                narrative_context=prompt,
                duration=shot.duration,
            )
            try:
                assets = await asyncio.wait_for(
                    provider.generate(plan, media_dir), timeout=45.0
                )
                if assets:
                    logger.info("media_resolved", scene=scene.scene_number, shot=shot.shot_number,
                                media_type=media_type, count=len(assets))
                    return assets
            except asyncio.TimeoutError:
                logger.debug("media_timeout", media_type=media_type, scene=scene.scene_number)
            except Exception as e:
                logger.debug("media_failed", error=str(e)[:60])

        return []

    def _get_provider(self, media_type: str):
        if media_type not in self._providers:
            if media_type == "stock_video":
                self._providers[media_type] = StockVideoProvider()
            elif media_type == "photo":
                self._providers[media_type] = PhotoProvider()
            elif media_type == "map":
                self._providers[media_type] = MapProvider()
            elif media_type == "infographic":
                self._providers[media_type] = InfographicProvider()
            elif media_type == "scientific_animation":
                self._providers[media_type] = ScientificAnimationProvider()
            else:
                return None
        return self._providers[media_type]

    @staticmethod
    def _shot_to_storytelling(shot: ShotPlan, scene) -> VisualStorytelling:
        return VisualStorytelling(
            emotion=shot.emotion,
            camera_style=shot.camera_type,
            camera_movement=shot.camera_movement,
            transition=shot.transition,
            focus_subject=shot.subject,
            secondary_subject=shot.secondary_subject,
            background_atmosphere=shot.atmosphere,
            lighting=shot.lighting,
            color_palette="",
            tempo=scene.pacing,
        )

    @staticmethod
    def _concat_clips(clips: list[str], output: str):
        if not clips:
            return
        if len(clips) == 1:
            shutil.copy(clips[0], output)
            return
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        tmp = Path(tempfile.mkdtemp())
        flist = tmp / "files.txt"
        flist.write_text("\n".join(f"file '{c}'" for c in clips))
        subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(flist), "-c", "copy", output],
            capture_output=True, timeout=120,
        )

    def _concat_and_mux(self, scene_videos: list[str], audio_path: str | None,
                        srt_path: str | None, output_path: str) -> str:
        if len(scene_videos) == 1:
            video_path = scene_videos[0]
        else:
            tmp = Path(tempfile.mkdtemp())
            flist = tmp / "files.txt"
            flist.write_text("\n".join(f"file '{v}'" for v in scene_videos))
            concat_path = str(tmp / "concat.mp4")
            subprocess.run([
                self.renderer.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                "-i", str(flist), "-c", "copy", concat_path,
            ], capture_output=True, timeout=120)
            video_path = concat_path

        return self.renderer._mux(video_path, audio_path, srt_path, output_path)

    async def _generate_audio(self, plan: ProductionPlan, uid: str) -> str | None:
        try:
            full_script = " ".join(s.narrative for s in plan.scenes)
            audio_dir = Path(settings.app_data_dir).expanduser().resolve() / "executor" / uid / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            out = str(audio_dir / "narration.mp3")
            import sys
            edge_tts = shutil.which("edge-tts") or os.path.join(os.path.dirname(sys.executable), "edge-tts")
            if not os.path.isfile(edge_tts):
                edge_tts = str(Path(sys.executable).parent / "edge-tts")
            voice = getattr(settings, "tts_default_voice", "hi-IN-SwaraNeural")
            proc = await asyncio.create_subprocess_exec(
                edge_tts, "--voice", voice, "--text", full_script, "--write-media", out,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=120.0)
            if os.path.isfile(out) and os.path.getsize(out) > 1024:
                return out
        except Exception as e:
            logger.warning("executor_audio_failed", error=str(e)[:60])
        return None

    @staticmethod
    def _generate_subtitles(plan: ProductionPlan, uid: str, audio_path: str | None = None) -> str | None:
        try:
            full_script = " ".join(s.narrative for s in plan.scenes)
            total_dur = plan.total_duration
            from services.subtitle.generator import SubtitleGenerator
            gen = SubtitleGenerator()
            srt = gen.generate(full_script, total_dur)
            if not srt:
                return None
            tmp = tempfile.NamedTemporaryFile(suffix=".srt", delete=False)
            tmp.write(srt.encode("utf-8"))
            tmp.close()
            return tmp.name
        except Exception as e:
            logger.debug("executor_subtitle_failed", error=str(e)[:60])
            return None

    @staticmethod
    def _dict_to_plan(data: dict) -> ProductionPlan:
        from services.director_v5.models import ScenePlan, ShotPlan
        scenes = []
        for sd in data.get("scenes", []):
            shots = [ShotPlan(**s) for s in sd.get("shots", [])]
            sd["shots"] = shots
            scenes.append(ScenePlan(**sd))
        data["scenes"] = scenes
        return ProductionPlan(**data)
