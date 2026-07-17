"""V5 Production Plan Models — the full creative blueprint for a documentary.

DirectorService outputs a ProductionPlan as JSON.
PlanExecutor reads the ProductionPlan and renders the video.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ShotPlan:
    shot_number: int
    camera_type: str              # Drone, Wide, Close-up, Macro, Underground, Aerial
    camera_movement: str          # Static, Slow Push, Crane Up, Crane Down, Pan, Track
    lens_style: str               # 24mm wide, 50mm standard, 100mm tele, macro
    lighting: str                 # Golden Hour, Moonlight, Dramatic, Natural, Warm
    subject: str
    secondary_subject: str = ""
    atmosphere: str = ""
    emotion: str = "Neutral"
    duration: float = 3.0
    cinematic_prompt: str = ""     # For AI video generation
    negative_prompt: str = ""      # What to avoid
    media_priority: list[str] = field(default_factory=lambda: ["stock_video", "photo"])
    transition: str = "Cut"
    visual_description: str = ""   # What the viewer should see
    shot_purpose: str = "context"  # hook, establish, detail, explain, reveal, close

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScenePlan:
    scene_number: int
    narrative: str                 # The narration sentence(s)
    purpose: str                   # hook, context, explanation, reveal, close
    emotion: str                   # Dominant emotion
    pacing: str                    # fast, slow, steady
    visual_goal: str               # What the audience should see/understand
    shots: list[ShotPlan] = field(default_factory=list)
    recommended_media_type: str = "stock_video"
    ai_video_prompt: str = ""
    stock_video_prompt: str = ""
    photo_prompt: str = ""
    map_requirements: Optional[dict] = None
    infographic_requirements: Optional[list[dict]] = None
    scientific_animation_requirements: Optional[dict] = None
    b_roll_suggestions: list[str] = field(default_factory=list)
    subtitle_emphasis: list[str] = field(default_factory=list)
    total_duration: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["shots"] = [s.to_dict() for s in self.shots]
        return d


@dataclass
class ProductionPlan:
    title: str
    total_duration: float
    scenes: list[ScenePlan] = field(default_factory=list)
    emotional_flow: list[str] = field(default_factory=list)
    pacing_structure: list[dict] = field(default_factory=list)
    music_mood: str = "Cinematic orchestral"
    sound_effects: list[str] = field(default_factory=list)
    subtitle_profile: str = "Standard"
    viewer_engagement_strategy: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "total_duration": round(self.total_duration, 1),
            "scenes": [s.to_dict() for s in self.scenes],
            "emotional_flow": self.emotional_flow,
            "pacing_structure": self.pacing_structure,
            "music_mood": self.music_mood,
            "sound_effects": self.sound_effects,
            "subtitle_profile": self.subtitle_profile,
            "viewer_engagement_strategy": self.viewer_engagement_strategy,
        }

    def to_json(self, indent: int = 2) -> str:
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
