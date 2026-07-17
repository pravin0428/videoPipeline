"""Phase 9 — Geography Engine: programmatic map generation.

Generates locator → state → district → village → zoom animation.
Wraps MapProvider from V4 with enhanced multi-level zoom.
"""

from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan
from services.media.providers.map import MapProvider

logger = get_logger()


class GeographyEngine:
    def __init__(self):
        self.map_provider = MapProvider()

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        assets = await self.map_provider.generate(plan, output_dir)

        if len(assets) >= 2:
            assets[0].metadata["zoom_level"] = "locator"
            assets[1].metadata["zoom_level"] = "zoom"
            assets[0].metadata["animation"] = "fade_in"
            assets[1].metadata["animation"] = "zoom_in"

        return assets
