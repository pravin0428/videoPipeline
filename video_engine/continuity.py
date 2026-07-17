from __future__ import annotations

from dataclasses import replace
from enum import Enum

from video_engine.config import CONTINUITY_FIELDS, DEFAULT_PROFILE
from video_engine.models import (
    PROFILE_DEFAULTS,
    Project,
    Scene,
    Shot,
    DocumentaryProfile,
    CameraMovement,
    CameraAngle,
    LensType,
    TimeOfDay,
    Weather,
    Mood,
    VisualEffect,
    MotionIntensity,
    CompositionType,
)

FIELD_ENUMS: dict[str, type[Enum]] = {
    "camera_movement": CameraMovement,
    "camera_angle": CameraAngle,
    "lens": LensType,
    "time_of_day": TimeOfDay,
    "weather": Weather,
    "mood": Mood,
    "visual_effects": VisualEffect,
    "motion_intensity": MotionIntensity,
    "composition": CompositionType,
}


def _parse_enum(value: str | Enum, enum_type: type[Enum]) -> Enum:
    if isinstance(value, enum_type):
        return value
    for member in enum_type:
        if member.value == value:
            return member
    raise ValueError(f"Unknown {enum_type.__name__}: {value}")


def _resolve_profile(profile_str: str) -> DocumentaryProfile:
    for p in DocumentaryProfile:
        if p.value == profile_str:
            return p
    return DEFAULT_PROFILE


class ContinuityManager:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.profile = _resolve_profile(project.profile)
        self.defaults = PROFILE_DEFAULTS.get(self.profile, {})

    def auto_fill_continuity(self) -> Project:
        updated_scenes: list[Scene] = []
        for scene in self.project.scenes:
            updated_shots: list[Shot] = []
            for shot in scene.shots:
                updated_shots.append(self._fill_shot(shot))
            updated_scenes.append(replace(scene, shots=updated_shots))
        return replace(self.project, scenes=updated_scenes)

    def _fill_shot(self, shot: Shot) -> Shot:
        kwargs: dict = {}
        for field_name in CONTINUITY_FIELDS:
            current = getattr(shot, field_name, None)
            if current is None or (
                isinstance(current, Enum) and current.value == "any"
            ):
                default = self.defaults.get(field_name)
                if default is not None:
                    kwargs[field_name] = default
        if not kwargs:
            return shot
        return replace(shot, **kwargs)

    def propagate(self, from_shot: Shot, to_shot: Shot) -> Shot:
        kwargs: dict = {}
        for field_name in CONTINUITY_FIELDS:
            to_val = getattr(to_shot, field_name, None)
            if to_val is None or (
                isinstance(to_val, Enum) and to_val.value == "any"
            ):
                from_val = getattr(from_shot, field_name, None)
                if from_val is not None:
                    kwargs[field_name] = from_val
        if not kwargs:
            return to_shot
        return replace(to_shot, **kwargs)

    def vary_for_scene(self, base_shot: Shot, scene_index: int, shot_index: int) -> Shot:
        kwargs: dict = {}
        for field_name in CONTINUITY_FIELDS:
            current = getattr(base_shot, field_name, None)
            enum_type = FIELD_ENUMS.get(field_name)
            if enum_type is None:
                continue
            members = list(enum_type)
            if len(members) <= 1:
                continue
            idx = (scene_index * 7 + shot_index * 13 + hash(field_name) % 31) % len(members)
            kwargs[field_name] = members[idx]
        return replace(base_shot, **kwargs)
