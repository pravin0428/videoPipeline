"""V5 Documentary Pipeline — AI Documentary Director.

Script → Sentence Understanding → Director Agent → Shot Planner → Visual Intent Planner
→ Media Planner → Asset Search → Asset Ranking → Scene Composer → Documentary Renderer
→ Video Quality Gate → Director Score → Final Video
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from core.config import settings
from core.logging import get_logger
from pipelines.video_short_v3 import ScenePlannerV3, VisualDirector, V3Scene
from services.asset.memory import AssetMemory
from services.asset.ranker import AssetRanker
from services.director.director_agent import DirectorAgent
from services.director.models import SceneBlueprint, VisualIntent
from services.geo.engine import GeographyEngine
from services.media.planner import MediaPlanner
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider
from services.media.providers.animation import ScientificAnimationProvider
from services.media.providers.infographic import InfographicProvider
from services.media.providers.map import MapProvider
from services.media.providers.photo import PhotoProvider
from services.media.providers.stock_video import StockVideoProvider
from services.quality.director_score import DirectorScoreCalculator
from services.quality.v5_gate import V5QualityGate
from services.renderer.documentary import DocumentaryRenderer
from services.scene.director import SceneDirector, VisualStorytelling
from services.science.engine import ScientificEngine

logger = get_logger()
V5_DIR = Path(settings.app_data_dir) / "v5"


class MediaGeneratorV5:
    def __init__(self):
        self.providers: dict[str, MediaProvider] = {
            "stock_video": StockVideoProvider(),
            "photo": PhotoProvider(),
            "map": MapProvider(),
            "infographic": InfographicProvider(),
            "scientific_animation": ScientificAnimationProvider(),
        }
        self.geo = GeographyEngine()
        self.science = ScientificEngine()
        self.ranker = AssetRanker()
        self.memory = AssetMemory()

    async def generate_for_shot(self, shot, intent: VisualIntent | None,
                                output_dir: Path) -> list[MediaAsset]:
        plan = self._shot_to_plan(shot, intent)
        assets = []

        if shot.media_type == "map":
            assets = await self.geo.generate(plan, output_dir)
        elif shot.media_type == "scientific_animation":
            assets = await self.science.generate(plan, output_dir)
        elif shot.media_type == "infographic":
            provider = self.providers["infographic"]
            if await provider.available():
                assets = await provider.generate(plan, output_dir)
        else:
            provider = self.providers.get(shot.media_type) or self.providers["stock_video"]
            if await provider.available():
                local = self.memory.search(
                    shot.description or shot.visual_description,
                    media_type=shot.media_type,
                    limit=3,
                )
                if local:
                    for a in local:
                        fp = a["file_path"]
                        if os.path.isfile(fp):
                            assets.append(MediaAsset(
                                media_type=shot.media_type,
                                file_path=fp,
                                duration=shot.duration,
                                source="local_memory",
                            ))
                            self.memory.record_usage(fp)

                if not assets:
                    new_assets = await provider.generate(plan, output_dir)
                    for a in new_assets:
                        self.memory.store(
                            a.file_path, a.source, a.media_type,
                            query=shot.description or shot.visual_description,
                            quality_score=0.6,
                        )
                    assets = new_assets

        if not assets:
            fallback = self.providers["stock_video"]
            if await fallback.available():
                assets = await fallback.generate(plan, output_dir)

        return assets

    def _shot_to_plan(self, shot, intent: VisualIntent | None) -> MediaPlan:
        desc = shot.visual_description or shot.description or ""
        if intent:
            desc = f"{intent.scene_description}. {intent.atmosphere}. {intent.lighting}. {desc}"
        return MediaPlan(
            scene_number=0,
            media_type=shot.media_type,
            narrative_context=desc,
            duration=shot.duration,
        )

    async def close(self):
        self.memory.close()
        for p in self.providers.values():
            if hasattr(p, "close"):
                await p.close()


class DocumentaryDirectorV5:
    def __init__(self, output_root: str | None = None):
        self.output_root = Path(output_root) if output_root else V5_DIR
        self.director = DirectorAgent()
        self.media_gen = MediaGeneratorV5()
        self.renderer = DocumentaryRenderer()
        self.quality_gate = V5QualityGate()
        self.score_calc = DirectorScoreCalculator()

    async def generate(self, title: str, script: str) -> dict:
        uid = uuid.uuid4().hex[:12]
        logger.info("v5_start", title=title, uid=uid)

        dirs = self._setup_dirs(uid)

        audio_path = await self._generate_tts(script, dirs["audio"])
        audio_dur = self._get_audio_duration(audio_path) if audio_path else 60.0
        logger.info("v5_audio_dur", duration=round(audio_dur, 1))

        blueprints, pacing = self.director.direct(script)
        self._retime_blueprints(blueprints, audio_dur)
        logger.info("v5_blueprints", count=len(blueprints), total_dur=round(sum(b.total_duration for b in blueprints), 1))

        scene_videos = []
        scene_metadata = []
        all_assets = []

        for i, blueprint in enumerate(blueprints):
            shot_videos = []
            for j, shot in enumerate(blueprint.shots):
                assets = await self.media_gen.generate_for_shot(
                    shot, blueprint.visual_intent, dirs["media"],
                )
                all_assets.extend(assets)

                if not assets:
                    assets = [MediaAsset(
                        media_type="stock_video",
                        file_path="",
                        duration=shot.duration,
                    )]

                for k, asset in enumerate(assets):
                    scene_dir = dirs["scenes"] / f"beat_{i:04d}_shot_{j:04d}"
                    scene_dir.mkdir(parents=True, exist_ok=True)
                    shot_path = str(scene_dir / f"frame_{k:04d}.mp4")

                    storytelling = VisualStorytelling(
                        emotion=shot.emotion,
                        camera_style=shot.camera,
                        camera_movement=shot.movement,
                        transition=shot.transition,
                        focus_subject=blueprint.visual_intent.primary_subject if blueprint.visual_intent else "",
                        secondary_subject=blueprint.visual_intent.secondary_subject if blueprint.visual_intent else "",
                        background_atmosphere=blueprint.visual_intent.atmosphere if blueprint.visual_intent else "",
                        lighting=blueprint.visual_intent.lighting if blueprint.visual_intent else "Natural",
                        color_palette=blueprint.visual_intent.color_palette if blueprint.visual_intent else "",
                        tempo=blueprint.rhythm or "steady",
                    )

                    shot_plan = MediaPlan(
                        scene_number=i + 1,
                        media_type=asset.media_type,
                        narrative_context=blueprint.beat.sentence,
                        duration=shot.duration,
                    )
                    self.renderer.render_scene(
                        [asset], shot_plan, storytelling, shot_path,
                    )
                    shot_videos.append(shot_path)

            if shot_videos:
                concat_path = str(dirs["scenes"] / f"beat_{i:04d}_combined.mp4")
                if len(shot_videos) == 1:
                    shutil.copy(shot_videos[0], concat_path)
                else:
                    flist = str(dirs["scenes"] / f"flist_{i:04d}.txt")
                    Path(flist).write_text("\n".join(f"file '{v}'" for v in shot_videos))
                    subprocess.run([
                        self.renderer.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                        "-i", flist, "-c", "copy", concat_path,
                    ], capture_output=True, timeout=120)
                scene_videos.append(concat_path)

            blueprint.beat.duration = blueprint.total_duration
            scene_metadata.append({
                "sentence": blueprint.beat.sentence[:60],
                "emotion": blueprint.dominant_emotion,
                "rhythm": blueprint.rhythm,
                "shots": len(blueprint.shots),
                "total_duration": round(blueprint.total_duration, 1),
                "media_types": list(set(s.media_type for s in blueprint.shots)),
                "cameras": list(set(s.camera for s in blueprint.shots)),
                "movements": list(set(s.movement for s in blueprint.shots)),
            })

        srt_path = self._generate_subtitles(script, blueprints, audio_dur)
        output_path = str(dirs["final"] / "final_v5.mp4")

        if audio_path and os.path.isfile(audio_path) and scene_videos:
            if len(scene_videos) == 1:
                video_path = scene_videos[0]
            else:
                flist = str(dirs["final"] / "files.txt")
                Path(flist).write_text("\n".join(f"file '{v}'" for v in scene_videos))
                concat_video = str(dirs["final"] / "concat.mp4")
                subprocess.run([
                    self.renderer.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", flist, "-c", "copy", concat_video,
                ], capture_output=True, timeout=120)
                video_path = concat_video
            final = self.renderer._mux(video_path, audio_path, srt_path, output_path)
        else:
            logger.warning("v5_no_audio_fallback")
            final = ""

        quality_meta = {
            "scene_count": len(scene_videos),
            "unique_assets": len(set(a.file_path for a in all_assets if a.file_path)),
            "media_types": list(set(a.media_type for a in all_assets)),
            "camera_styles": [s.camera for bp in blueprints for s in bp.shots],
            "emotions": [bp.dominant_emotion for bp in blueprints],
            "total_assets": len(all_assets),
        }

        quality_result = await self.quality_gate.validate(final, quality_meta) if final else {"passed": False, "checks": {}}

        director_score = self.score_calc.calculate(final, scene_metadata, quality_result)

        report = {
            "uid": uid,
            "title": title,
            "duration": round(audio_dur, 1),
            "quality": quality_result,
            "director_score": director_score.to_dict(),
            "scenes": scene_metadata,
            "pacing": {
                "hook_type": pacing.hook_type,
                "has_mystery": pacing.has_mystery,
                "has_reveal": pacing.has_reveal,
                "emotional_arc": pacing.emotional_arc,
            },
        }

        report_path = str(dirs["debug"] / "report.json")
        Path(report_path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("v5_report", path=report_path)

        if not quality_result.get("passed", False):
            logger.warning("v5_quality_gate", summary=quality_result.get("summary", ""))

        logger.info("v5_complete", output=final, duration=round(audio_dur, 1))
        report["video_path"] = final
        return report

    def _setup_dirs(self, uid: str) -> dict:
        d = {k: self.output_root.expanduser().resolve() / uid / k for k in ("media", "scenes", "audio", "final", "debug")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _retime_blueprints(blueprints: list[SceneBlueprint], target_dur: float):
        if not blueprints:
            return
        current = sum(b.total_duration for b in blueprints)
        if current == 0:
            return
        scale = target_dur / current
        for b in blueprints:
            b.total_duration = max(2.0, min(12.0, b.total_duration * scale))
            for s in b.shots:
                s.duration = max(1.0, min(8.0, s.duration * scale))
        total = sum(b.total_duration for b in blueprints)
        scale = target_dur / total
        for b in blueprints:
            b.total_duration = max(2.0, min(12.0, b.total_duration * scale))

    async def _generate_tts(self, script: str, audio_dir: Path) -> str | None:
        try:
            import sys
            edge_tts = shutil.which("edge-tts") or os.path.join(os.path.dirname(sys.executable), "edge-tts")
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
                logger.info("v5_tts_done", path=out)
                return out
        except Exception as e:
            logger.warning("v5_tts_failed", error=str(e)[:80])
        return None

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        try:
            r = subprocess.run([
                shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe",
                "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1", audio_path,
            ], capture_output=True, text=True, timeout=15)
            return max(10.0, float(r.stdout.strip().split("=")[-1]))
        except Exception:
            return 60.0

    @staticmethod
    def _generate_subtitles(script: str, blueprints: list, total: float) -> str | None:
        try:
            from services.subtitle.generator import SubtitleGenerator
            gen = SubtitleGenerator()
            srt = gen.generate(script, total)
            if not srt:
                return None
            tmp = tempfile.NamedTemporaryFile(suffix=".srt", delete=False)
            tmp.write(srt.encode("utf-8"))
            tmp.close()
            return tmp.name
        except Exception as e:
            logger.debug("v5_subtitle_failed", error=str(e)[:60])
            return None
