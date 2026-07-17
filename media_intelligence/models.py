from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional


class MediaType(str, Enum):
    STOCK_VIDEO = "stock_video"
    STOCK_PHOTO = "stock_photo"
    MAP = "map"
    INFOGRAPHIC = "infographic"
    SCIENTIFIC_ANIMATION = "scientific_animation"
    AI_VIDEO = "ai_video"

    @property
    def label(self) -> str:
        return {
            "stock_video": "Stock Video",
            "stock_photo": "Stock Photo + Ken Burns",
            "map": "Map / Geographic",
            "infographic": "Infographic / Data Visualization",
            "scientific_animation": "Scientific Animation",
            "ai_video": "AI-Generated Video",
        }[self.value]

    @property
    def priority(self) -> int:
        """Lower = higher priority for educational use."""
        return {
            "map": 1,
            "infographic": 2,
            "scientific_animation": 3,
            "stock_video": 4,
            "stock_photo": 5,
            "ai_video": 6,
        }[self.value]


@dataclass
class SentenceFeatures:
    text: str
    has_location: bool = False
    has_direction: bool = False
    has_boundaries: bool = False
    has_statistics: bool = False
    has_comparison: bool = False
    has_numbers: bool = False
    has_process: bool = False
    has_cause_effect: bool = False
    has_steps: bool = False
    has_concrete_visual: bool = False
    has_movement: bool = False
    has_natural_phenomenon: bool = False
    has_historical_ref: bool = False
    has_time_period: bool = False
    has_abstract_concept: bool = False
    has_biological_ref: bool = False
    has_geological_ref: bool = False
    has_architectural_ref: bool = False
    has_named_place: bool = False
    has_cultural_ref: bool = False
    has_ritual: bool = False
    has_emotion: bool = False
    has_sensory_detail: bool = False
    has_contrast: bool = False
    has_scale: bool = False
    key_nouns: list[str] = field(default_factory=list)
    key_verbs: list[str] = field(default_factory=list)
    key_adjectives: list[str] = field(default_factory=list)
    location_terms: list[str] = field(default_factory=list)
    numbers_found: list[str] = field(default_factory=list)

    @property
    def dominant_quality(self) -> str:
        candidates = []
        if self.has_location:
            candidates.append("location")
        if self.has_statistics or self.has_comparison or self.has_numbers:
            candidates.append("data")
        if self.has_process or self.has_cause_effect or self.has_steps:
            candidates.append("process")
        if self.has_concrete_visual:
            candidates.append("visual")
        if self.has_abstract_concept:
            candidates.append("abstract")
        if self.has_historical_ref or self.has_time_period:
            candidates.append("historical")
        if self.has_biological_ref or self.has_geological_ref:
            candidates.append("science")
        if self.has_architectural_ref or self.has_cultural_ref:
            candidates.append("cultural")
        return candidates[0] if candidates else "general"


@dataclass
class MediaPlan:
    sentence: str
    media_type: MediaType
    confidence: float
    reasoning: str
    visual_elements: list[str] = field(default_factory=list)
    search_prompt: str = ""
    generation_prompt: str = ""
    negative_prompt: str = ""
    fallback_order: list[MediaType] = field(default_factory=list)
    quality_criteria: list[str] = field(default_factory=list)
    suggested_duration: float = 5.0
    camera_style: str = ""
    visual_goal: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["media_type"] = self.media_type.value
        d["fallback_order"] = [m.value for m in self.fallback_order]
        return d


FALLBACK_CHAINS: dict[MediaType, list[MediaType]] = {
    MediaType.MAP: [MediaType.STOCK_VIDEO, MediaType.STOCK_PHOTO, MediaType.INFOGRAPHIC],
    MediaType.INFOGRAPHIC: [
        MediaType.SCIENTIFIC_ANIMATION, MediaType.STOCK_VIDEO, MediaType.STOCK_PHOTO,
    ],
    MediaType.SCIENTIFIC_ANIMATION: [
        MediaType.INFOGRAPHIC, MediaType.STOCK_VIDEO, MediaType.AI_VIDEO,
    ],
    MediaType.STOCK_VIDEO: [
        MediaType.STOCK_PHOTO, MediaType.MAP, MediaType.AI_VIDEO,
    ],
    MediaType.STOCK_PHOTO: [
        MediaType.STOCK_VIDEO, MediaType.MAP, MediaType.AI_VIDEO,
    ],
    MediaType.AI_VIDEO: [
        MediaType.STOCK_VIDEO, MediaType.STOCK_PHOTO, MediaType.MAP,
    ],
}

CAMERA_STYLES: dict[str, str] = {
    "awe": "Slow sweeping wide shot, golden hour lighting, dramatic clouds",
    "wonder": "Slow push-in reveal, soft lens flare, shallow depth of field",
    "somber": "Static tripod shot, overcast soft light, desaturated tones",
    "dramatic": "Low angle hero shot, dramatic side lighting, contrasty shadows",
    "educational": "Clean well-lit shot, medium focal length, informative framing",
    "intimate": "Close-up with shallow depth of field, warm backlight, handheld feel",
    "epic": "Drone aerial shot, ultra-wide lens, sunset golden light, vast landscape",
    "historical": "Sepia-toned, archival texture, static frame, grainy film look",
    "neutral": "Standard documentary framing, even lighting, tripod-stable",
}
