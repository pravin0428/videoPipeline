"""Subtitle (SRT) generation from scene narration with timing."""
import os

from video_engine.models import Project
from video_engine.utils.logging import LOG


def generate_subtitles(project: Project, output_path: str, start_offset: float = 0.0) -> str:
    LOG.info("Generating subtitles...")

    lines: list[str] = []
    current_time = start_offset
    entry_num = 1

    for scene in project.scenes:
        text = scene.narration
        dur = scene.tts_duration or 3.0
        if not text:
            continue

        start = current_time
        end = current_time + dur

        def fmt(t: float) -> str:
            return f"{int(t // 3600):02d}:{int((t % 3600) // 60):02d}:{t % 60:06.3f}".replace(".", ",")

        lines.append(str(entry_num))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(text)
        lines.append("")
        entry_num += 1
        current_time = end

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    LOG.done(f"SRT: {entry_num - 1} entries → {output_path}")
    return output_path


def generate_timed_subtitles(
    shots_timeline: list[dict],
    output_path: str,
) -> str:
    lines: list[str] = []
    for i, entry in enumerate(shots_timeline, 1):
        start = entry["start"]
        end = entry["end"]
        text = entry["text"]

        def fmt(t: float) -> str:
            return f"{int(t // 3600):02d}:{int((t % 3600) // 60):02d}:{t % 60:06.3f}".replace(".", ",")

        lines.append(str(i))
        lines.append(f"{fmt(start)} --> {fmt(end)}")
        lines.append(text)
        lines.append("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path
