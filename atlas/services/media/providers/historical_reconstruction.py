"""Historical Reconstruction Provider — stub for period reenactment / archival-style visuals.

When the planner detects historical content (ancient, empire, century, history),
this provider generates a placeholder that can later be replaced with real archival
footage, historical reconstructions, or AI-generated period scenes.
"""
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class HistoricalReconstructionProvider(MediaProvider):
    media_type = "historical_reconstruction"

    async def available(self) -> bool:
        return False

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        logger.warning("historical_reconstruction_not_implemented", scene=plan.scene_number)
        return []
