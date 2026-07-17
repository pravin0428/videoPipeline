from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TTSResult:
    audio_data: bytes
    duration_seconds: float
    mime_type: str
    file_size: int
    stored_path: str = ""


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str = "hi-IN-SwaraNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        ...
