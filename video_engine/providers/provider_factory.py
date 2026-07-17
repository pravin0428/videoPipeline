from __future__ import annotations

from typing import Optional

from video_engine.providers.base_provider import BaseProvider
from video_engine.providers.pexels_provider import PexelsProvider
from video_engine.providers.veo_provider import VeoProvider
from video_engine.providers.kling_provider import KlingProvider
from video_engine.providers.runway_provider import RunwayProvider
from video_engine.providers.pixverse_provider import PixVerseProvider
from video_engine.providers.hailuo_provider import HailuoProvider

_REGISTRY: dict[str, type[BaseProvider]] = {
    "pexels": PexelsProvider,
    "veo": VeoProvider,
    "kling": KlingProvider,
    "runway": RunwayProvider,
    "pixverse": PixVerseProvider,
    "hailuo": HailuoProvider,
}


class ProviderFactory:
    @classmethod
    def create(cls, name: str, config: Optional[dict] = None) -> BaseProvider:
        normalized = name.strip().lower()
        provider_cls = _REGISTRY.get(normalized)
        if provider_cls is None:
            available = ", ".join(sorted(_REGISTRY))
            raise ValueError(
                f"Unknown provider '{name}'. "
                f"Available providers: {available}"
            )
        return provider_cls(config=config or {})

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseProvider]) -> None:
        _REGISTRY[name.strip().lower()] = provider_cls

    @classmethod
    def available(cls) -> list[str]:
        return list(_REGISTRY.keys())
