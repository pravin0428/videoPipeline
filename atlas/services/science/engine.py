"""Phase 10 — Scientific Engine: animation/diagram selection for science content.

When narration explains science, history, astronomy, biology, geology,
automatically routes to the right visualization provider.
"""

from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan
from services.media.providers.animation import ScientificAnimationProvider
from services.media.providers.infographic import InfographicProvider

logger = get_logger()


class ScientificEngine:
    def __init__(self):
        self.animation = ScientificAnimationProvider()
        self.infographic = InfographicProvider()

    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        concept = self._detect_concept(plan.narrative_context)
        sub_plan = MediaPlan(
            scene_number=plan.scene_number,
            media_type="scientific_animation",
            narrative_context=plan.narrative_context,
            duration=plan.duration,
        )

        if concept in ("root", "fungus", "network", "cell", "volcano", "gravity", "dna", "solar"):
            assets = await self.animation.generate(sub_plan, output_dir)
            if assets:
                return assets

        assets = await self.infographic.generate(sub_plan, output_dir)
        return assets

    @staticmethod
    def _detect_concept(text: str) -> str | None:
        lower = text.lower()
        concepts = [
            ("root", ["जड़", "root", "roots", "underground", "जड़ों"]),
            ("fungus", ["फंगस", "fungus", "fungi", "mycorrhizal", "mushroom"]),
            ("network", ["नेटवर्क", "network", "web", "जाल", "connected"]),
            ("cell", ["कोशिका", "cell", "cellular", "सूक्ष्म"]),
            ("volcano", ["ज्वालामुखी", "volcano", "volcanic", "lava"]),
            ("gravity", ["गुरुत्वाकर्षण", "gravity", "gravitational"]),
            ("dna", ["डीएनए", "DNA", "genetic", "gene"]),
            ("solar", ["सौर", "solar system", "ग्रह", "planet", "star"]),
        ]
        for concept, keywords in concepts:
            if any(k in lower for k in keywords):
                return concept
        return None
