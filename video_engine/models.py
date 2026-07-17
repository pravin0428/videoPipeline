from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, asdict
from enum import Enum
from typing import Optional, get_type_hints


class ShotType(Enum):
    REAL = "real"
    PHOTO = "photo"
    TEXT = "text"


class CameraMovement(Enum):
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"
    TRUCK_LEFT = "truck_left"
    TRUCK_RIGHT = "truck_right"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"
    SLOW_PAN = "slow_pan"
    PUSH_IN = "push_in"
    PULL_OUT = "pull_out"
    AERIAL = "aerial"
    DRONE = "drone"
    TRACKING = "tracking"
    ORBIT = "orbit"


class CameraAngle(Enum):
    EYE_LEVEL = "eye_level"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"
    OVERHEAD = "overhead"
    WORM_EYE = "worm_eye"
    SHOULDER = "shoulder"
    PROFILE = "profile"
    THREE_QUARTER = "three_quarter"
    DUTCH = "dutch"
    AERIAL_VIEW = "aerial_view"
    FIRST_PERSON = "first_person"
    MACRO = "macro"
    EXTREME_CLOSEUP = "extreme_closeup"
    WIDE = "wide"
    ULTRA_WIDE = "ultra_wide"


class LensType(Enum):
    STANDARD = "standard"
    WIDE_ANGLE = "wide_angle"
    ULTRA_WIDE = "ultra_wide"
    TELEPHOTO = "telephoto"
    MACRO = "macro"
    FISHEYE = "fisheye"
    ANARMORPHIC = "anamorphic"
    LONG_LENS = "long_lens"
    SHORT_LENS = "short_lens"
    ZOOM = "zoom"
    PRIME = "prime"
    TILT_SHIFT = "tilt_shift"


class TimeOfDay(Enum):
    MORNING = "morning"
    GOLDEN_HOUR = "golden_hour"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    SUNSET = "sunset"
    TWILIGHT = "twilight"
    NIGHT = "night"
    BLUE_HOUR = "blue_hour"
    DAWN = "dawn"
    DUSK = "dusk"
    OVERCAST = "overcast"
    ANY = "any"


class Weather(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    MIST = "mist"
    WINDY = "windy"
    HUMID = "humid"
    DROUGHT = "drought"
    ANY = "any"


class Mood(Enum):
    SERENE = "serene"
    DRAMATIC = "dramatic"
    MYSTERIOUS = "mysterious"
    EPIC = "epic"
    INTIMATE = "intimate"
    CONTEMPLATIVE = "contemplative"
    TENSE = "tense"
    PEACEFUL = "peaceful"
    AWE = "awe"
    SOMBER = "somber"
    JOYFUL = "joyful"
    NEUTRAL = "neutral"
    HOPEFUL = "hopeful"
    MELANCHOLIC = "melancholic"
    SACRED = "sacred"
    URGENT = "urgent"
    WONDER = "wonder"


class VisualEffect(Enum):
    NONE = "none"
    SLOW_MOTION = "slow_motion"
    TIMELAPSE = "timelapse"
    HYPERLAPSE = "hyperlapse"
    NIGHT_VISION = "night_vision"
    INFRARED = "infrared"
    THERMAL = "thermal"
    BLACK_AND_WHITE = "black_and_white"
    SEPIA = "sepia"
    VIGNETTE = "vignette"
    FADE = "fade"
    SOFT_FOCUS = "soft_focus"
    DREAMY = "dreamy"
    FILM_GRAIN = "film_grain"
    MINIATURE = "miniature"
    LENS_FLARE = "lens_flare"
    HDR = "hdr"


class CompositionType(Enum):
    RULE_OF_THIRDS = "rule_of_thirds"
    CENTER = "center"
    LEADING_LINES = "leading_lines"
    SYMMETRY = "symmetry"
    DIAGONAL = "diagonal"
    FRAMING = "framing"
    GOLDEN_RATIO = "golden_ratio"
    DEPTH = "depth"
    PATTERN = "pattern"
    TEXTURE = "texture"
    BALANCE = "balance"
    DYNAMIC = "dynamic"
    MINIMALIST = "minimalist"
    ABSTRACT = "abstract"


class MotionIntensity(Enum):
    STATIC = "static"
    GENTLE = "gentle"
    MODERATE = "moderate"
    DYNAMIC = "dynamic"
    INTENSE = "intense"
    FAST = "fast"


class DocumentaryProfile(Enum):
    NATURALISTIC = "naturalistic"
    CINEMATIC = "cinematic"
    BBC_EARTH = "bbc_earth"
    NATGEO = "natgeo"
    PLANET_EARTH = "planet_earth"
    BLUE_PLANET = "blue_planet"
    ATENborough = "attenborough"
    WILDLIFE = "wildlife"
    MACRO_WONDER = "macro_wonder"
    AERIAL_SERENITY = "aerial_serenity"
    SCIENTIFIC = "scientific"
    DOCUMENTARY_DRAMA = "documentary_drama"
    TIMELAPSE_WORLD = "timelapse_world"
    CULTURAL_PORTRAIT = "cultural_portrait"


PROFILE_DEFAULTS: dict[DocumentaryProfile, dict] = {
    DocumentaryProfile.NATURALISTIC: {
        "camera_movement": CameraMovement.STATIC,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.STANDARD,
        "time_of_day": TimeOfDay.ANY,
        "weather": Weather.ANY,
        "mood": Mood.NEUTRAL,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "medium",
        "color_palette": "natural",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.CINEMATIC: {
        "camera_movement": CameraMovement.STEADICAM,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.ANARMORPHIC,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.EPIC,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.MODERATE,
        "depth_of_field": "shallow",
        "color_palette": "warm",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.BBC_EARTH: {
        "camera_movement": CameraMovement.SLOW_PAN,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.TELEPHOTO,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.AWE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "shallow",
        "color_palette": "rich_warm",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.NATGEO: {
        "camera_movement": CameraMovement.STEADICAM,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.TELEPHOTO,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.WONDER,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.MODERATE,
        "depth_of_field": "shallow",
        "color_palette": "vibrant",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.PLANET_EARTH: {
        "camera_movement": CameraMovement.DOLLY_IN,
        "camera_angle": CameraAngle.WIDE,
        "lens": LensType.WIDE_ANGLE,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.EPIC,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "deep",
        "color_palette": "vibrant",
        "composition": CompositionType.LEADING_LINES,
    },
    DocumentaryProfile.BLUE_PLANET: {
        "camera_movement": CameraMovement.SLOW_PAN,
        "camera_angle": CameraAngle.OVERHEAD,
        "lens": LensType.WIDE_ANGLE,
        "time_of_day": TimeOfDay.MIDDAY,
        "weather": Weather.CLEAR,
        "mood": Mood.SERENE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "deep",
        "color_palette": "cool_blue",
        "composition": CompositionType.LEADING_LINES,
    },
    DocumentaryProfile.ATENborough: {
        "camera_movement": CameraMovement.SLOW_PAN,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.ZOOM,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.CONTEMPLATIVE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "shallow",
        "color_palette": "warm",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.WILDLIFE: {
        "camera_movement": CameraMovement.PAN_LEFT,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.TELEPHOTO,
        "time_of_day": TimeOfDay.MORNING,
        "weather": Weather.CLEAR,
        "mood": Mood.INTIMATE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.MODERATE,
        "depth_of_field": "very_shallow",
        "color_palette": "natural",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
    DocumentaryProfile.MACRO_WONDER: {
        "camera_movement": CameraMovement.DOLLY_IN,
        "camera_angle": CameraAngle.MACRO,
        "lens": LensType.MACRO,
        "time_of_day": TimeOfDay.MORNING,
        "weather": Weather.CLEAR,
        "mood": Mood.WONDER,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.STATIC,
        "depth_of_field": "extremely_shallow",
        "color_palette": "vibrant",
        "composition": CompositionType.DEPTH,
    },
    DocumentaryProfile.AERIAL_SERENITY: {
        "camera_movement": CameraMovement.DRONE,
        "camera_angle": CameraAngle.AERIAL_VIEW,
        "lens": LensType.WIDE_ANGLE,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.SERENE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "deep",
        "color_palette": "natural",
        "composition": CompositionType.LEADING_LINES,
    },
    DocumentaryProfile.SCIENTIFIC: {
        "camera_movement": CameraMovement.STATIC,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.STANDARD,
        "time_of_day": TimeOfDay.MIDDAY,
        "weather": Weather.CLEAR,
        "mood": Mood.NEUTRAL,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.STATIC,
        "depth_of_field": "deep",
        "color_palette": "neutral",
        "composition": CompositionType.CENTER,
    },
    DocumentaryProfile.DOCUMENTARY_DRAMA: {
        "camera_movement": CameraMovement.HANDHELD,
        "camera_angle": CameraAngle.SHOULDER,
        "lens": LensType.ZOOM,
        "time_of_day": TimeOfDay.TWILIGHT,
        "weather": Weather.OVERCAST,
        "mood": Mood.TENSE,
        "visual_effects": VisualEffect.FILM_GRAIN,
        "motion_intensity": MotionIntensity.DYNAMIC,
        "depth_of_field": "medium",
        "color_palette": "desaturated",
        "composition": CompositionType.DYNAMIC,
    },
    DocumentaryProfile.TIMELAPSE_WORLD: {
        "camera_movement": CameraMovement.STATIC,
        "camera_angle": CameraAngle.WIDE,
        "lens": LensType.WIDE_ANGLE,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.EPIC,
        "visual_effects": VisualEffect.TIMELAPSE,
        "motion_intensity": MotionIntensity.FAST,
        "depth_of_field": "deep",
        "color_palette": "vibrant",
        "composition": CompositionType.LEADING_LINES,
    },
    DocumentaryProfile.CULTURAL_PORTRAIT: {
        "camera_movement": CameraMovement.SLOW_PAN,
        "camera_angle": CameraAngle.EYE_LEVEL,
        "lens": LensType.STANDARD,
        "time_of_day": TimeOfDay.GOLDEN_HOUR,
        "weather": Weather.CLEAR,
        "mood": Mood.INTIMATE,
        "visual_effects": VisualEffect.NONE,
        "motion_intensity": MotionIntensity.GENTLE,
        "depth_of_field": "medium",
        "color_palette": "warm",
        "composition": CompositionType.RULE_OF_THIRDS,
    },
}


@dataclass
class Shot:
    shot_id: str
    narration: str = ""
    duration_seconds: float = 5.0
    shot_type: ShotType = ShotType.REAL
    subject: str = ""
    action: str = ""
    environment: str = ""
    camera_direction: str = ""

    camera_movement: CameraMovement = CameraMovement.STATIC
    camera_angle: CameraAngle = CameraAngle.EYE_LEVEL
    lens: LensType = LensType.STANDARD
    time_of_day: TimeOfDay = TimeOfDay.ANY
    weather: Weather = Weather.ANY
    mood: Mood = Mood.NEUTRAL
    visual_effects: VisualEffect = VisualEffect.NONE
    motion_intensity: MotionIntensity = MotionIntensity.GENTLE
    composition: CompositionType = CompositionType.RULE_OF_THIRDS
    depth_of_field: str = "deep"
    color_palette: str = "natural"
    negative_prompt: str = ""
    focus_subject: str = ""
    lighting_reference: str = ""
    profile: str = "naturalistic"
    search_prompt: str = ""
    video_path: str = ""

    def to_dict(self) -> dict:
        d = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, Enum):
                d[f.name] = v.value
            else:
                d[f.name] = v
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Shot:
        hints = get_type_hints(cls)
        kwargs = {}
        for f in fields(cls):
            if f.name not in d:
                continue
            ftype = hints.get(f.name, f.type)
            if isinstance(ftype, str):
                kwargs[f.name] = d[f.name]
            elif isinstance(ftype, type) and issubclass(ftype, Enum):
                kwargs[f.name] = ftype(d[f.name])
            elif (
                hasattr(ftype, "__origin__")
                and ftype.__origin__ is Optional
                and isinstance(ftype.__args__[0], type)
                and issubclass(ftype.__args__[0], Enum)
            ):
                kwargs[f.name] = ftype.__args__[0](d[f.name])
            else:
                kwargs[f.name] = d[f.name]
        return cls(**kwargs)


@dataclass
class Scene:
    scene_id: str
    title: str
    narration: str
    tts_duration: float = 0.0
    shots: list[Shot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "narration": self.narration,
            "tts_duration": self.tts_duration,
            "shots": [s.to_dict() for s in self.shots],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Scene:
        return cls(
            scene_id=d["scene_id"],
            title=d["title"],
            narration=d["narration"],
            tts_duration=float(d.get("tts_duration", 0)),
            shots=[Shot.from_dict(s) for s in d.get("shots", [])],
        )


@dataclass
class Project:
    title: str
    output_path: str
    scenes: list[Scene] = field(default_factory=list)
    profile: str = "naturalistic"
    voice: str = "hi-IN-SwaraNeural"
    language: str = "hi"
    fps: int = 30
    resolution: str = "1080x1920"
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "output_path": self.output_path,
            "description": self.description,
            "profile": self.profile,
            "voice": self.voice,
            "language": self.language,
            "fps": self.fps,
            "resolution": self.resolution,
            "scenes": [s.to_dict() for s in self.scenes],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> Project:
        return cls(
            title=d["title"],
            output_path=d["output_path"],
            description=d.get("description", ""),
            profile=d.get("profile", "naturalistic"),
            voice=d.get("voice", "hi-IN-SwaraNeural"),
            language=d.get("language", "hi"),
            fps=d.get("fps", 30),
            resolution=d.get("resolution", "1080x1920"),
            scenes=[Scene.from_dict(s) for s in d.get("scenes", [])],
        )

    @classmethod
    def from_json(cls, text: str) -> Project:
        return cls.from_dict(json.loads(text))
