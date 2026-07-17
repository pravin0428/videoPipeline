"""Load project definitions from JSON files or convert existing scripts."""
import json
import os
import sys
from pathlib import Path

from video_engine.errors import ProjectLoadError
from video_engine.models import Project, Scene, Shot, ShotType
from video_engine.utils.logging import LOG


def load_project(path: str) -> Project:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise ProjectLoadError(
            f"Project file not found: {abs_path}",
            module="project_loader",
            hint="Provide a valid path to a project.json file, or use --script <name>",
        )

    LOG.info(f"Loading project from {abs_path}")
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ProjectLoadError(
            f"Invalid JSON in {abs_path}: {e}",
            module="project_loader",
            hint="Check the file for syntax errors",
        )

    if "title" not in data or "scenes" not in data:
        raise ProjectLoadError(
            "Project JSON must contain 'title' and 'scenes'",
            module="project_loader",
            hint="Use an existing project file as a template",
        )

    if not data.get("output_path"):
        data["output_path"] = str(Path(__file__).parent / "output" / data["title"])

    return Project.from_dict(data)


def load_script(script_id: str) -> Project:
    LOG.info(f"Loading script '{script_id}' from existing library")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from media_lab.make_documentary import SCRIPTS
    except ImportError as e:
        raise ProjectLoadError(
            f"Cannot import SCRIPTS from media_lab: {e}",
            module="project_loader",
            hint="Ensure media_lab/make_documentary.py exists",
        )

    if script_id not in SCRIPTS:
        raise ProjectLoadError(
            f"Unknown script '{script_id}'. Available: {list(SCRIPTS.keys())}",
            module="project_loader",
        )

    config = SCRIPTS[script_id]
    scenes_raw = config["scenes"]
    scene_queries = config.get("scene_queries", {})

    scenes: list[Scene] = []
    for i, s in enumerate(scenes_raw):
        queries = scene_queries.get(i, [s.get("en", s.get("hi", ""))[:60]])
        shot_duration = max(5.0, 4.0)

        narration = s.get("hi", "") or s.get("en", "")
        shots = [
            Shot(
                shot_type=ShotType.REAL,
                duration_seconds=shot_duration,
                search_prompt=queries[0] if queries else s.get("en", "")[:60],
                subject=script_id,
            ),
        ]

        scenes.append(Scene(
            scene_id=str(i + 1),
            title=s.get("en", script_id)[:40],
            narration=narration,
            shots=shots,
        ))

    output_path = str(Path(__file__).parent / "output" / script_id)

    return Project(
        title=script_id,
        scenes=scenes,
        output_path=output_path,
    )


def auto_detect_input(arg: str) -> Project:
    if arg.endswith(".json"):
        return load_project(arg)

    try:
        return load_script(arg)
    except ProjectLoadError:
        pass

    raise ProjectLoadError(
        f"Cannot interpret input: {arg}",
        module="project_loader",
        hint="Provide a path to a project.json file or a known script name",
    )
