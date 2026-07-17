from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MediaPlan:
    scene_number: int
    media_type: str  # ai_video, stock_video, photo, map, infographic, scientific_animation, historical_reconstruction
    reason: str = ""
    narrative_context: str = ""
    duration: float = 6.0


@dataclass
class MediaAsset:
    media_type: str
    file_path: str
    duration: float = 0.0
    width: int = 1080
    height: int = 1920
    source: str = ""
    metadata: dict = field(default_factory=dict)


class MediaProvider(ABC):
    media_type: str = ""

    @abstractmethod
    async def generate(self, plan: MediaPlan, output_dir: Path) -> list[MediaAsset]:
        ...

    @abstractmethod
    async def available(self) -> bool:
        ...

    def can_handle(self, media_type: str) -> bool:
        return media_type == self.media_type
