import re
import textwrap

from core.logging import get_logger

logger = get_logger()


class SubtitleGenerator:
    def generate(self, script_text: str, total_duration: float) -> str:
        lines = self._split_into_cues(script_text)
        total_chars = sum(len(l) for l in lines)
        if total_chars == 0:
            return ""

        srt_parts: list[str] = []
        current_time = 0.0

        for i, line in enumerate(lines):
            char_ratio = len(line) / total_chars
            duration = max(total_duration * char_ratio, 1.5)
            if i == len(lines) - 1:
                duration = total_duration - current_time

            start = self._format_time(current_time)
            end = self._format_time(current_time + duration)
            srt_parts.append(f"{i + 1}\n{start} --> {end}\n{line}\n")

            current_time += duration

        return "\n".join(srt_parts)

    def _split_into_cues(self, text: str) -> list[str]:
        raw = re.split(r"(?<=[।\.!\?])", text)
        raw = [r.strip() for r in raw if r.strip()]

        result: list[str] = []
        for part in raw:
            if len(part) > 80:
                wrapped = textwrap.fill(part, width=80).split("\n")
                result.extend(wrapped)
            else:
                result.append(part)
        return result

    def _format_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
