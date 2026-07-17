"""AI Video Provider — abstraction for future AI video generators.

Pluggable backends can be registered via set_backend().
Built-in backends: WanBackend, CogVideoXBackend, LTXVideoBackend,
HunyuanVideoBackend, ComfyUIBackend (all stubs — too slow for local M2).

Extend by subclassing AIVideoBackend and calling AIVideoProvider.set_backend().
"""
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class AIVideoBackend:
    name = "base"

    async def generate_clip(self, prompt: str, duration: float, output_path: str) -> bool:
        raise NotImplementedError


class WanBackend(AIVideoBackend):
    name = "wan"


class CogVideoXBackend(AIVideoBackend):
    name = "cogvideox"


class LTXVideoBackend(AIVideoBackend):
    name = "ltx_video"


class HunyuanVideoBackend(AIVideoBackend):
    name = "hunyuan_video"


class ComfyUIBackend(AIVideoBackend):
    name = "comfyui"


class AIVideoProvider(MediaProvider):
    media_type = "ai_video"

    def __init__(self):
        self._backend: AIVideoBackend | None = None

    def set_backend(self, backend: AIVideoBackend):
        self._backend = backend
        logger.info("ai_video_backend_set", backend=backend.name)

    async def available(self) -> bool:
        return self._backend is not None

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        if not self._backend:
            logger.warning("ai_video_no_backend")
            return []

        prompt = self._build_prompt(plan)
        output_path = str(output_dir / f"ai_{plan.scene_number:04d}.mp4")
        ok = await self._backend.generate_clip(prompt, plan.duration, output_path)
        if ok:
            return [MediaAsset(
                media_type="ai_video",
                file_path=output_path,
                duration=plan.duration,
                source=f"ai_{self._backend.name}",
            )]
        return []

    @staticmethod
    def _build_prompt(plan: MediaPlan) -> str:
        context = plan.narrative_context[:150]
        return (
            f"Cinematic documentary shot. {context}. "
            f"High quality, photorealistic, 1080x1920 portrait, "
            f"smooth motion, professional lighting."
        )
