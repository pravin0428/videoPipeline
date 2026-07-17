import os
import uuid
from pathlib import Path

import httpx

from core.config import settings
from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()

CACHE_DIR = Path(settings.app_data_dir) / "map_cache"


class MapProvider(MediaProvider):
    media_type = "map"

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def available(self) -> bool:
        return True

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        output_dir.mkdir(parents=True, exist_ok=True)
        context = plan.narrative_context[:200]

        location = self._extract_location(context)
        frames = []

        base = await self._render_map(location, "locator", output_dir)
        if base:
            frames.append(base)

        zoom_out = await self._render_map(location, "zoom", output_dir)
        if zoom_out:
            frames.append(zoom_out)

        assets = []
        for i, path in enumerate(frames):
            assets.append(MediaAsset(
                media_type="map",
                file_path=path,
                duration=plan.duration / max(len(frames), 1),
                source="atlas_map",
                metadata={"frame": i, "location": location},
            ))
        return assets

    @staticmethod
    def _extract_location(text: str) -> str:
        import re
        patterns = [
            r"(?:में स्थित|located in|जिला|district of|शहर|city of)\s*([\u0900-\u097F\s]{3,30})",
            r"([\u0900-\u097F\s]{3,30})\s*(?:जिला|district)",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(1).strip()[:30]
        return text.split()[-1] if text else "India"

    async def _render_map(self, location: str, style: str, output_dir: Path) -> str | None:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams['font.sans-serif'] = ['Kohinoor Devanagari', 'Devanagari Sangam MN', 'Devanagari MT'] + matplotlib.rcParams.get('font.sans-serif', [])
        matplotlib.rcParams['font.family'] = 'sans-serif'
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        cache_key = f"map_{hash(location)}_{style}.png"
        cache_path = CACHE_DIR / cache_key
        if cache_path.exists():
            return str(cache_path)

        fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        base_color = "#1a2a3a"
        accent = "#e8c84a"
        fig.patch.set_facecolor(base_color)
        ax.set_facecolor(base_color)

        if style == "locator":
            ax.text(50, 75, "INDIA", fontsize=28, color="white",
                    ha="center", va="center", fontweight="bold", fontfamily="sans-serif")
            rect = mpatches.FancyBboxPatch((30, 40), 40, 30,
                                            boxstyle="round,pad=0.1",
                                            facecolor=accent, alpha=0.3, edgecolor=accent,
                                            linewidth=2)
            ax.add_patch(rect)
            ax.text(50, 55, location, fontsize=18, color=accent,
                    ha="center", va="center", fontfamily="sans-serif")
            ax.text(50, 12, "📍 Location", fontsize=14, color="gray",
                    ha="center", va="center")
        elif style == "zoom":
            ax.text(50, 50, "🔍", fontsize=60, ha="center", va="center")
            ax.text(50, 30, location, fontsize=20, color="white",
                    ha="center", va="center", fontweight="bold")
            ax.text(50, 20, "Maharashtra", fontsize=16, color=accent,
                    ha="center", va="center")

        path = str(output_dir / f"{uuid.uuid4().hex[:12]}_{style}.png")
        fig.savefig(path, bbox_inches="tight", pad_inches=0, facecolor=base_color)
        plt.close(fig)
        return path
