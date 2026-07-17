import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from core.config import settings
from core.logging import get_logger
from services.tts.provider import BaseTTSProvider, TTSResult

logger = get_logger()

_EDGE_TTS_BIN: str | None = None


def _resolve_edge_tts() -> str:
    global _EDGE_TTS_BIN
    if _EDGE_TTS_BIN:
        return _EDGE_TTS_BIN
    candidates = [
        os.path.join(os.path.dirname(sys.executable), "edge-tts"),
        shutil.which("edge-tts") or "",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            _EDGE_TTS_BIN = c
            return c
    return "edge-tts"


class EdgeTTSProvider(BaseTTSProvider):
    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = output_dir or os.path.join(settings.app_data_dir, "audio")

    async def synthesize(
        self,
        text: str,
        voice: str = "hi-IN-SwaraNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = tmp.name
        tmp.close()

        try:
            cmd = [
                _resolve_edge_tts(),
                "--voice", voice,
                "--text", text,
                "--rate", rate,
                "--pitch", pitch,
                "--write-media", output_path,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error("edge_tts_failed", returncode=proc.returncode, stderr=stderr.decode())
                raise RuntimeError(f"edge-tts failed: {stderr.decode()}")

            with open(output_path, "rb") as f:
                audio_data = f.read()

            file_size = len(audio_data)
            duration = self._estimate_duration(text)

            import uuid
            safe_voice = voice.replace("/", "_").replace(" ", "_")
            dest_path = os.path.join(self.output_dir, f"{uuid.uuid4().hex}_{safe_voice}.mp3")
            os.rename(output_path, dest_path)

            return TTSResult(
                audio_data=audio_data,
                duration_seconds=duration,
                mime_type="audio/mp3",
                file_size=file_size,
                stored_path=dest_path,
            )

        except FileNotFoundError:
            logger.error("edge_tts_not_installed")
            self._cleanup(output_path)
            raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts")
        except Exception as e:
            logger.error("tts_synthesis_failed", error=str(e))
            self._cleanup(output_path)
            raise

    def _cleanup(self, path: str) -> None:
        if os.path.exists(path):
            os.unlink(path)

    def _estimate_duration(self, text: str) -> float:
        word_count = len(text.split())
        words_per_second = 3.5
        estimated = word_count / words_per_second
        return round(max(estimated, 5.0), 1)
