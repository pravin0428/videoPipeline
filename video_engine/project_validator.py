"""Validate project structure before pipeline execution."""
from video_engine.errors import ProjectValidationError
from video_engine.models import Project, Scene, Shot, ShotType
from video_engine.utils.logging import LOG

VALID_SHOT_TYPES = {e.value for e in ShotType}


def validate_project(project: Project) -> Project:
    if not project.title:
        raise ProjectValidationError("Project title is required", module="validator")

    if not project.scenes:
        raise ProjectValidationError(
            "Project must have at least one scene",
            module="validator",
        )

    if project.fps <= 0:
        raise ProjectValidationError(
            f"Invalid fps: {project.fps}",
            module="validator",
            hint="Use a positive integer (e.g., 30)",
        )

    valid_res = project.resolution.split("x")
    if len(valid_res) != 2 or not all(d.isdigit() for d in valid_res):
        raise ProjectValidationError(
            f"Invalid resolution: {project.resolution}",
            module="validator",
            hint="Use WxH format (e.g., 1080x1920)",
        )

    if not project.output_path:
        raise ProjectValidationError(
            "Output path is not set",
            module="validator",
        )

    for scene in project.scenes:
        _validate_scene(scene, project)

    LOG.info(f"Project '{project.title}' — {len(project.scenes)} scenes validated")
    return project


def _validate_scene(scene: Scene, project: Project):
    if not scene.narration:
        raise ProjectValidationError(
            f"Scene {scene.scene_id} has no narration text",
            module="validator",
            scene_id=scene.scene_id,
        )

    if not scene.shots:
        raise ProjectValidationError(
            f"Scene {scene.scene_id} has no shots",
            module="validator",
            scene_id=scene.scene_id,
            hint="Each scene must define at least one shot",
        )

    for shot in scene.shots:
        _validate_shot(shot, scene)


def _validate_shot(shot: Shot, scene: Scene):
    if shot.shot_type and shot.shot_type.value not in VALID_SHOT_TYPES:
        raise ProjectValidationError(
            f"Scene {scene.scene_id}: invalid shot_type '{shot.shot_type.value}'. "
            f"Valid: {VALID_SHOT_TYPES}",
            module="validator",
            scene_id=scene.scene_id,
        )

    if shot.duration_seconds <= 0:
        raise ProjectValidationError(
            f"Scene {scene.scene_id}: shot duration must be positive "
            f"(got {shot.duration_seconds})",
            module="validator",
            scene_id=scene.scene_id,
        )
