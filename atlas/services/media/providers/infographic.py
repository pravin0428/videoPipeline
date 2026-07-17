import os
import re
import uuid
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan, MediaProvider

logger = get_logger()


class InfographicProvider(MediaProvider):
    media_type = "infographic"

    def __init__(self):
        self.DATA_PATTERNS = [
            (re.compile(r"(\d+[.,]?\d*)\s*(करोड़|million|लाख)"), "population"),
            (re.compile(r"(\d+)\s*(किमी|km|मीटर|meter|फीट|feet)"), "measurement"),
            (re.compile(r"(\d{3,4})\s*(ईसा|ई\.|बीसी|AD|BC|सन)"), "date"),
            (re.compile(r"(\d+)\s*प्रतिशत|(\d+)\s*percent"), "percentage"),
            (re.compile(r"(\d+[.,]?\d*)\s*(अरब|billion)"), "large_number"),
        ]

    async def available(self) -> bool:
        return True

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        output_dir.mkdir(parents=True, exist_ok=True)
        context = plan.narrative_context[:200]

        data_points = self._extract_data(context)
        if not data_points:
            return []

        frames = []
        for dp in data_points:
            path = await self._render_infographic(dp, output_dir)
            if path:
                frames.append(path)

        assets = []
        for i, path in enumerate(frames):
            assets.append(MediaAsset(
                media_type="infographic",
                file_path=path,
                duration=min(3.0, plan.duration / max(len(frames), 1)),
                source="atlas_infographic",
                metadata={"data_point": str(data_points[i]) if i < len(data_points) else ""},
            ))
        return assets

    def _extract_data(self, text: str) -> list[dict]:
        results = []
        for pattern, dtype in self.DATA_PATTERNS:
            for m in pattern.finditer(text):
                results.append({"value": m.group(0), "type": dtype, "context": text[:80]})
        return results[:3]

    async def _render_infographic(self, data: dict, output_dir: Path) -> str | None:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams['font.sans-serif'] = ['Kohinoor Devanagari', 'Devanagari Sangam MN', 'Devanagari MT'] + matplotlib.rcParams.get('font.sans-serif', [])
        matplotlib.rcParams['font.family'] = 'sans-serif'
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        fig, ax = plt.subplots(figsize=(10.8, 19.2), dpi=100)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.axis("off")

        bg = "#0d1b2a"
        accent = "#e8c84a"
        fig.patch.set_facecolor(bg)
        ax.set_facecolor(bg)

        value = data.get("value", "")
        dtype = data.get("type", "data")

        title_map = {
            "population": "जनसंख्या",
            "measurement": "माप",
            "date": "तिथि",
            "percentage": "प्रतिशत",
            "large_number": "संख्या",
        }

        icon_map = {
            "population": "👥",
            "measurement": "📏",
            "date": "📅",
            "percentage": "📊",
            "large_number": "🔢",
        }

        icon = icon_map.get(dtype, "📊")
        title = title_map.get(dtype, "डेटा")

        box = mpatches.FancyBboxPatch((15, 30), 70, 50,
                                       boxstyle="round,pad=0.2",
                                       facecolor="#1b2d45", edgecolor=accent,
                                       linewidth=2)
        ax.add_patch(box)
        ax.text(50, 65, icon, fontsize=40, ha="center", va="center")
        ax.text(50, 50, value, fontsize=32, color="white",
                ha="center", va="center", fontweight="bold")
        ax.text(50, 38, title, fontsize=16, color=accent,
                ha="center", va="center")

        path = str(output_dir / f"info_{uuid.uuid4().hex[:12]}.png")
        fig.savefig(path, bbox_inches="tight", pad_inches=0, facecolor=bg)
        plt.close(fig)
        return path
