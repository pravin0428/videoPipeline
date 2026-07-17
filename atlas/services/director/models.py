"""V5 Core Data Models — the editorial language of the Director Agent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Rhythm(Enum):
    FAST = "fast"
    SLOW = "slow"
    STEADY = "steady"


class Emotion(Enum):
    WONDER = "Wonder"
    MYSTERY = "Mystery"
    CURIOSITY = "Curiosity"
    TENSION = "Tension"
    CALM = "Calm"
    HOPE = "Hope"
    AMAZEMENT = "Amazement"
    NOSTALGIA = "Nostalgia"
    RESPECT = "Respect"
    FEAR = "Fear"
    SURPRISE = "Surprise"
    REFLECTION = "Reflection"


class CameraStyle(Enum):
    DRONE = "Drone"
    WIDE = "Wide"
    CLOSE_UP = "Close-up"
    MACRO = "Macro"
    UNDERGROUND = "Underground"
    TRACKING = "Tracking"
    AERIAL = "Aerial"
    CINEMATIC = "Cinematic"
    POV = "POV"
    ARCHITECTURE = "Architecture"
    HANDHELD = "Handheld"
    SLOW_MOTION = "Slow Motion"
    HYPERLAPSE = "Hyperlapse"


class CameraMovement(Enum):
    STATIC = "Static"
    SLOW_PUSH = "Slow Push"
    CRANE_UP = "Crane Up"
    CRANE_DOWN = "Crane Down"
    PAN_LEFT = "Pan Left"
    PAN_RIGHT = "Pan Right"
    TRACK_FORWARD = "Track Forward"
    TRACK_BACKWARD = "Track Backward"
    TILT_UP = "Tilt Up"
    TILT_DOWN = "Tilt Down"
    ZOOM_IN = "Zoom In"
    ZOOM_OUT = "Zoom Out"
    DOLLY = "Dolly"
    STEADICAM = "Steadicam"


class Transition(Enum):
    CUT = "Cut"
    DISSOLVE = "Dissolve"
    FADE_IN = "Fade In"
    FADE_OUT = "Fade Out"
    CROSSFADE = "Crossfade"
    WIPE = "Wipe"
    SWIPE = "Swipe"
    MATCH_CUT = "Match Cut"


class MediaType(Enum):
    AI_VIDEO = "ai_video"
    STOCK_VIDEO = "stock_video"
    PHOTO = "photo"
    MAP = "map"
    INFOGRAPHIC = "infographic"
    SCIENTIFIC_ANIMATION = "scientific_animation"
    HISTORICAL_RECONSTRUCTION = "historical_reconstruction"
    B_ROLL = "b_roll"


class ShotPurpose(Enum):
    HOOK = "hook"
    CONTEXT = "context"
    DETAIL = "detail"
    REVEAL = "reveal"
    EMOTION = "emotion"
    EXPLANATION = "explanation"
    TRANSITION = "transition"
    ESTABLISH = "establish"
    CLOSE = "close"


@dataclass
class StoryBeat:
    sentence: str
    purpose: str = ""
    emotion: str = ""
    importance: int = 5
    viewer_question: str = ""
    visual_goal: str = ""
    duration: float = 0.0
    rhythm: str = "steady"


@dataclass
class Shot:
    description: str
    camera: str = "Cinematic"
    movement: str = "Static"
    duration: float = 3.0
    emotion: str = "Wonder"
    purpose: str = "context"
    transition: str = "Cut"
    media_type: str = "stock_video"
    visual_description: str = ""
    b_roll: list[str] = field(default_factory=list)

    @property
    def is_video(self) -> bool:
        return self.media_type in ("stock_video", "ai_video", "b_roll")


@dataclass
class VisualIntent:
    scene_description: str
    primary_subject: str
    secondary_subject: str = ""
    background: str = ""
    lighting: str = "Natural"
    color_palette: str = "Warm"
    atmosphere: str = ""
    camera_instructions: str = ""
    reference_style: str = ""


@dataclass
class SceneBlueprint:
    beat: StoryBeat
    shots: list[Shot] = field(default_factory=list)
    visual_intent: Optional[VisualIntent] = None
    dominant_emotion: str = "Wonder"
    rhythm: str = "steady"
    total_duration: float = 0.0
    video_descriptions: list[str] = field(default_factory=list)
    image_descriptions: list[str] = field(default_factory=list)
    b_roll_needs: list[str] = field(default_factory=list)


@dataclass
class DocumentaryPacing:
    structure: list[tuple[str, str]] = field(default_factory=list)
    hook_type: str = "question"
    has_mystery: bool = False
    has_reveal: bool = False
    emotional_arc: list[str] = field(default_factory=list)
    rhythm_map: dict[int, str] = field(default_factory=dict)


@dataclass
class DirectorScore:
    visual_storytelling: float = 0.0
    documentary_feel: float = 0.0
    visual_diversity: float = 0.0
    cinematic_quality: float = 0.0
    emotional_flow: float = 0.0
    educational_value: float = 0.0
    retention_prediction: float = 0.0
    overall: float = 0.0

    def to_dict(self) -> dict:
        return {
            "visual_storytelling": round(self.visual_storytelling, 1),
            "documentary_feel": round(self.documentary_feel, 1),
            "visual_diversity": round(self.visual_diversity, 1),
            "cinematic_quality": round(self.cinematic_quality, 1),
            "emotional_flow": round(self.emotional_flow, 1),
            "educational_value": round(self.educational_value, 1),
            "retention_prediction": round(self.retention_prediction, 1),
            "overall": round(self.overall, 1),
        }
