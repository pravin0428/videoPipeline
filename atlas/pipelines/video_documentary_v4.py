"""V4 Documentary Pipeline — AI Documentary Production Engine.

Script → Scene Planner → Media Planner → Asset Planner → Media Generator → Documentary Renderer → Video
"""
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import httpx

from core.config import settings
from core.logging import get_logger
from pipelines.video_short_v3 import (
    ScenePlannerV3, V3Scene, V3SceneRender, VisualDirector, TOTAL_TARGET_DURATION,
)
from services.media.planner import MediaPlanner
from services.media.providers.base import MediaAsset, MediaPlan
from services.media.providers.stock_video import StockVideoProvider
from services.media.providers.ai_video import AIVideoProvider
from services.media.providers.photo import PhotoProvider
from services.media.providers.map import MapProvider
from services.media.providers.infographic import InfographicProvider
from services.media.providers.animation import ScientificAnimationProvider
from services.media.providers.historical_reconstruction import HistoricalReconstructionProvider
from services.quality.video_gate import VideoQualityGate
from services.renderer.documentary import DocumentaryRenderer
from services.scene.director import SceneDirector, VisualStorytelling

logger = get_logger()
V4_DIR = Path(settings.app_data_dir) / "v4"


class MediaGenerator:
    def __init__(self):
        self.providers: dict[str, any] = {
            "stock_video": StockVideoProvider(),
            "ai_video": AIVideoProvider(),
            "photo": PhotoProvider(),
            "map": MapProvider(),
            "infographic": InfographicProvider(),
            "scientific_animation": ScientificAnimationProvider(),
            "historical_reconstruction": HistoricalReconstructionProvider(),
        }
        self.preference_order = ["stock_video", "ai_video", "scientific_animation",
                                  "map", "infographic", "historical_reconstruction", "photo"]

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        primary = plan.media_type
        provider = self.providers.get(primary)
        if provider and await provider.available():
            assets = await provider.generate(plan, output_dir)
            if assets:
                return assets

        for mtype in self.preference_order:
            if mtype == primary:
                continue
            fallback = self.providers.get(mtype)
            if fallback and await fallback.available():
                assets = await fallback.generate(plan, output_dir)
                if assets:
                    logger.info("media_fallback", scene=plan.scene_number,
                                planned=primary, actual=mtype)
                    return assets

        return []

    async def close(self):
        for p in self.providers.values():
            if hasattr(p, "close"):
                await p.close()


class DocumentaryGenerator:
    def __init__(self, output_root: str | None = None, topic_research_data: dict | None = None):
        self.output_root = Path(output_root) if output_root else V4_DIR
        self.planner = ScenePlannerV3()
        self.media_planner = MediaPlanner()
        self.media_gen = MediaGenerator()
        self.renderer = DocumentaryRenderer()
        self.quality_gate = VideoQualityGate()
        self._topic_research_data = topic_research_data or {}

    async def generate(self, title: str, script: str, output_filename: str = "final_v4.mp4") -> dict:
        uid = uuid.uuid4().hex[:12]
        logger.info("v4_start", title=title, uid=uid)

        dirs = self._setup_dirs(uid)

        audio_path = await self._generate_tts(script, dirs["audio"])
        audio_dur = self._get_audio_duration(audio_path) if audio_path else TOTAL_TARGET_DURATION
        logger.info("v4_audio_dur", duration=round(audio_dur, 1))

        scenes = await self.planner.plan(script)
        scenes = [VisualDirector.direct(s) for s in scenes]
        scenes = self._retime_scenes(scenes, audio_dur)
        logger.info("v4_scenes", count=len(scenes), total_dur=round(sum(s.duration for s in scenes), 1))

        scene_plans: list[MediaPlan] = []
        scene_storytelling: list[VisualStorytelling] = []
        scene_assets: list[list[MediaAsset]] = []

        for scene in scenes:
            plan = self.media_planner.plan(
                scene_number=scene.scene_number,
                narration=scene.narration,
                visual_goal=scene.visual_goal,
                duration=scene.duration,
            )
            scene_plans.append(plan)
            story = SceneDirector.direct(scene.narration, scene.visual_goal, scene.shot_type)
            scene_storytelling.append(story)

            logger.info("v4_media_plan", scene=scene.scene_number,
                        media_type=plan.media_type, reason=plan.reason[:60])

            try:
                assets = await asyncio.wait_for(
                    self.media_gen.generate(plan, dirs["media"]), timeout=45.0
                )
            except asyncio.TimeoutError:
                logger.warning("media_gen_timeout", scene=scene.scene_number, media_type=plan.media_type)
                assets = []
            scene_assets.append(assets)

            logger.info("v4_media_assets", scene=scene.scene_number,
                        count=len(assets), types=[a.media_type for a in assets])

        scene_videos = []
        for i, scene in enumerate(scenes):
            scene_dir = dirs["scenes"] / f"scene_{scene.scene_number:04d}"
            scene_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(scene_dir / "scene.mp4")
            self.renderer.render_scene(
                scene_assets[i], scene_plans[i], scene_storytelling[i], output_path,
            )
            scene_videos.append(output_path)
            logger.info("v4_scene_rendered", scene=scene.scene_number, path=output_path)

        srt_path = await self._generate_subtitles(script, scenes, scene_videos)
        output_path = str(dirs["final"] / output_filename)

        if audio_path and os.path.isfile(audio_path):
            final = self.renderer.render_scenes_concat(scene_videos, audio_path, srt_path, output_path)
        else:
            concat_path = str(dirs["final"] / "no_audio.mp4")
            if len(scene_videos) == 1:
                shutil.copy(scene_videos[0], concat_path)
            else:
                flist = str(dirs["final"] / "files.txt")
                Path(flist).write_text("\n".join(f"file '{v}'" for v in scene_videos))
                subprocess.run([
                    self.renderer.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", flist, "-c", "copy", concat_path,
                ], capture_output=True, timeout=120)
            final = self.renderer._mux(concat_path, None, srt_path, output_path)

        all_asset_paths = [a.file_path for assets in scene_assets for a in assets]
        quality_result = await self.quality_gate.validate(final, {
            "scene_count": len(scene_videos),
            "unique_assets": len(set(all_asset_paths)),
            "media_types": list(set(a.media_type for assets in scene_assets for a in assets)),
        })

        if not quality_result["passed"]:
            logger.warning("v4_quality_gate", summary=quality_result["summary"])

        report = {
            "uid": uid,
            "title": title,
            "scenes": [
                {
                    "number": s.scene_number,
                    "duration": s.duration,
                    "media_type": p.media_type,
                    "emotion": st.emotion,
                    "camera": st.camera_style,
                    "movement": st.camera_movement,
                    "assets": len(a),
                }
                for s, p, st, a in zip(scenes, scene_plans, scene_storytelling, scene_assets)
            ],
        }
        report_path = str(dirs["debug"] / "report.json")
        Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("v4_report", path=report_path)

        logger.info("v4_complete", output=final, duration=round(sum(s.duration for s in scenes), 1))
        return {
            "video_path": final,
            "duration": round(sum(s.duration for s in scenes), 1),
            "quality": quality_result,
            "uid": uid,
            "scenes": report["scenes"],
        }

    def _setup_dirs(self, uid: str) -> dict:
        d = {k: self.output_root / uid / k for k in ("media", "scenes", "audio", "final", "debug")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _retime_scenes(scenes: list[V3Scene], target_dur: float) -> list[V3Scene]:
        if not scenes:
            return scenes
        current = sum(s.duration for s in scenes)
        if current == 0:
            return scenes
        scale = target_dur / current
        for s in scenes:
            s.duration = max(2.0, min(12.0, s.duration * scale))
        total = sum(s.duration for s in scenes)
        scale = target_dur / total
        for s in scenes:
            s.duration = max(2.0, min(12.0, s.duration * scale))
        start = 0.0
        for s in scenes:
            s.start_time = round(start, 1)
            start += s.duration
        return scenes

    async def _generate_tts(self, script: str, audio_dir: Path) -> str | None:
        try:
            import sys
            edge_tts = (shutil.which("edge-tts") or os.path.join(os.path.dirname(sys.executable), "edge-tts"))
            if not os.path.isfile(edge_tts):
                edge_tts = str(Path(sys.executable).parent / "edge-tts")
            out = str(audio_dir / "narration.mp3")
            voice = getattr(settings, "tts_default_voice", "hi-IN-SwaraNeural")
            proc = await asyncio.create_subprocess_exec(
                edge_tts, "--voice", voice, "--text", script, "--write-media", out,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=120.0)
            if os.path.isfile(out) and os.path.getsize(out) > 1024:
                logger.info("v4_tts_done", path=out)
                return out
        except Exception as e:
            logger.warning("v4_tts_failed", error=str(e)[:80])
        return None

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        if not audio_path or not os.path.isfile(audio_path):
            return TOTAL_TARGET_DURATION
        try:
            r = subprocess.run([
                shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe",
                "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1", audio_path,
            ], capture_output=True, text=True, timeout=15)
            return max(10.0, float(r.stdout.strip().split("=")[-1]))
        except Exception:
            return TOTAL_TARGET_DURATION

    async def _generate_subtitles(self, script: str, scenes: list[V3Scene],
                                   scene_videos: list[str]) -> str | None:
        try:
            from services.subtitle.generator import SubtitleGenerator
            gen = SubtitleGenerator()
            total = sum(s.duration for s in scenes)
            srt = gen.generate(script, total)
            if not srt:
                return None
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".srt", delete=False)
            tmp.write(srt.encode("utf-8"))
            tmp.close()
            return tmp.name
        except Exception as e:
            logger.debug("subtitle_gen_failed", error=str(e)[:60])
            return None
