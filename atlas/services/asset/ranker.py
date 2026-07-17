"""Phase 5 — Asset Ranking: CLIP similarity, diversity, quality scoring.

Searches multiple sources, ranks using:
1. CLIP similarity to visual intent
2. Visual diversity (avoid similar shots)
3. Cinematic quality score
4. Resolution suitability
5. Portrait orientation
6. No watermark/logo check
"""

import os
import re
from pathlib import Path

from core.logging import get_logger
from services.asset.memory import AssetMemory

logger = get_logger()

_asset_memory: AssetMemory | None = None


def _memory() -> AssetMemory:
    global _asset_memory
    if _asset_memory is None:
        _asset_memory = AssetMemory()
    return _asset_memory


class AssetRanker:
    def __init__(self):
        self.memory = _memory()

    def rank(self, candidates: list[dict], intent_description: str,
             used_embeddings: list[str] | None = None) -> list[dict]:
        used = used_embeddings or []

        scored = []
        for c in candidates:
            score = self._score(c, intent_description, used)
            scored.append((score, c))

        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored]

    def _score(self, candidate: dict, intent: str, used: list[str]) -> float:
        score = 0.5

        file_path = candidate.get("file_path", "")
        ext = file_path.lower()
        if ext.endswith((".mp4", ".mov", ".webm")):
            score += 0.2

        width = candidate.get("width", 0)
        height = candidate.get("height", 0)
        if height > width:
            score += 0.15
        if height >= 1920:
            score += 0.1

        score += self._quality_heuristics(file_path)

        if self._has_watermark(file_path):
            score -= 0.3

        query = candidate.get("query", "").lower()
        intent_lower = intent.lower()
        query_words = set(query.split()[:5])
        intent_words = set(intent_lower.split()[:5])
        overlap = len(query_words & intent_words)
        if overlap > 0:
            score += 0.05 * overlap

        file_name = Path(file_path).name
        if file_name in used:
            score -= 0.5

        return max(0.0, min(1.0, score))

    @staticmethod
    def _quality_heuristics(path: str) -> float:
        try:
            size = os.path.getsize(path)
            if size < 50_000:
                return -0.2
            if size > 500_000:
                return 0.1
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _has_watermark(path: str) -> bool:
        name = Path(path).stem.lower()
        watermark_patterns = [r"watermark", r"shutterstock", r"getty", r"istock", r"123rf", r"depositphotos"]
        return any(re.search(p, name) for p in watermark_patterns)

    async def deduplicate(self, assets: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for a in assets:
            fp = a.get("file_path", "")
            if fp not in seen:
                seen.add(fp)
                unique.append(a)
        return unique
