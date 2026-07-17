from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VideoAsset:
    local_path: str = ""
    provider_name: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: int = 30
    generation_time: float = 0.0
    metadata: dict = field(default_factory=dict)
    quality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "local_path": self.local_path,
            "provider_name": self.provider_name,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "generation_time": self.generation_time,
            "metadata": self.metadata,
            "quality_score": self.quality_score,
        }


class BaseProvider(ABC):
    provider_name: str = "base"

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self._initialized = False
        self._metrics: dict[str, Any] = {}

    @abstractmethod
    def initialize(self) -> None:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...

    def supports_images(self) -> bool:
        return False

    def supports_video(self) -> bool:
        return True

    @abstractmethod
    def generate(self, prompt: str, options: Optional[dict] = None) -> VideoAsset:
        ...

    def download(self, asset: VideoAsset) -> str:
        return asset.local_path

    def cleanup(self) -> None:
        pass

    def get_metrics(self) -> dict:
        return dict(self._metrics)

    def _record_generation(self, asset: VideoAsset, start_time: float) -> None:
        asset.generation_time = time.time() - start_time
        asset.provider_name = self.provider_name
        self._metrics.setdefault("total_generations", 0)
        self._metrics["total_generations"] += 1
        self._metrics.setdefault("total_time", 0.0)
        self._metrics["total_time"] += asset.generation_time
