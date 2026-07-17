"""
Enhanced Planner: transforms basic MediaPlans into rich shot sequences
for professional documentary quality.

Editorial Intelligence improvements:
- Subject Identity Engine: every shot scored for subject relevance
- Entity-First Search: exact landmark → area → district → state → generic
- Visual Narrative Sequences: story-driven shots per sentence
- Hero Shot Detection: reserve premium clips for climax moments
- Category-Specific Playbooks: wildlife, science, history, location
- Emotional Storytelling: emotion-defined visual motifs per scene
- Shot Continuity Tracking: consecutive shots feel connected
- Enhanced Quality Gate: 12-dimension documentary quality score
"""
import random
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter
from .models import MediaType, MediaPlan, SentenceFeatures, FALLBACK_CHAINS


# ── Shot Types ──

SHOT_TYPES = [
    "aerial", "wide", "medium", "close_up",
    "macro", "detail", "transition", "pov",
]

SHOT_PURPOSES = [
    "establish", "narrate", "emphasize",
    "retain", "b_roll", "conclude",
]

NARRATIVE_POSITIONS = ["hook", "reveal", "explain", "discover", "conclude"]

# ── Documentary Categories ──
EDITORIAL_CATEGORIES = [
    "location", "wildlife", "science", "history", "cultural", "general",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "location": ["fort", "lake", "mountain", "river", "village", "city", "temple",
                 "coast", "beach", "island", "valley", "desert", "forest"],
    "wildlife": ["tiger", "lion", "elephant", "bird", "fish", "animal", "turtle",
                 "leopard", "deer", "monkey", "snake", "bear", "wolf"],
    "science": ["science", "physics", "chemistry", "biology", "space", "atom",
                "molecule", "light", "energy", "gravity", "evolution", "dna"],
    "history": ["history", "ancient", "medieval", "king", "queen", "empire",
                "battle", "revolution", "civilization", "dynasty"],
    "cultural": ["culture", "tradition", "festival", "ritual", "dance", "music",
                 "ceremony", "folk", "art", "craft"],
}

# ── Emotion Detection ──
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "awe": ["beautiful", "amazing", "incredible", "spectacular", "magnificent",
            "breathtaking", "stunning", "wonder", "majestic", "glorious",
            "this is the", "this is a", "the most", "one of the", "is here",
            "reminds us", "symbol of", "pride of"],
    "curiosity": ["do you know", "ever wondered", "secret", "mystery",
                  "hidden", "unknown", "surprising", "uncover", "discover"],
    "wonder": ["miracle", "magical", "extraordinary", "remarkable", "fascinating",
               "marvel", "astonishing", "unbelievable", "prodigy",
               "dream", "imagine", "beyond"],
    "faith": ["faith", "divine", "blessing", "prayer", "sacred", "spiritual",
              "holy", "reverence", "devotion", "temple", "blessing"],
    "peace": ["peaceful", "serene", "tranquil", "quiet", "calm", "gentle",
              "harmony", "soothing", "relaxing", "silent", "still water",
              "gentle", "resting"],
    "fear": ["danger", "threaten", "endangered", "extinct", "deadly",
             "frightening", "terrifying", "precarious", "alarming",
             "if luck", "rarely seen", "disappearing"],
    "excitement": ["exciting", "thrilling", "adventure", "discovery", "triumph",
                   "victory", "celebration", "journey", "quest", "enter",
                   "arrive", "welcome", "possible"],
    "melancholy": ["lost", "disappeared", "forgotten", "vanished", "ruins",
                   "abandoned", "crumbled", "fading", "memory", "reminds us",
                   "once was", "no more", "only"],
}

EMOTION_VISUAL_MOTIFS: dict[str, list[str]] = {
    "awe": ["golden hour light", "vast landscape", "dramatic clouds", "sun rays"],
    "curiosity": ["hidden detail", "slow reveal", "shadow play", "mysterious light"],
    "wonder": ["wide majestic view", "slow push-in", "light through trees", "reflection"],
    "faith": ["soft warm light", "candle flame", "ritual objects", "peaceful atmosphere"],
    "peace": ["still water", "gentle waves", "soft breeze", "quiet morning"],
    "fear": ["dark shadows", "intense eyes", "sudden movement", "dangerous terrain"],
    "excitement": ["dynamic movement", "fast cutting", "dramatic angle", "energy"],
    "melancholy": ["fading light", "empty spaces", "ruins", "soft desaturated tones"],
}

# ── Entity-First Search Hierarchy ──
# Each level is a function(subject_context) → search terms
ENTITY_SEARCH_LEVELS = [
    "exact_landmark",
    "exact_subject",
    "nearby_area",
    "same_region",
    "feature_type",
    "generic_context",
]


# ── Visual Narrative Templates ──
# Each narrative position has a sequence of visual beats per category
# Beat: {shot_type, purpose, camera_motion, continuity_tag, focus_template}
# focus_template gets .format(subject=..., feature=...)

LOCATION_NARRATIVE = {
    "hook": [
        {"shot_type": "aerial", "purpose": "establish", "camera_motion": "drone flyover",
         "continuity_tag": "approach", "focus_template": "Aerial approach to {subject}"},
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "static tripod",
         "continuity_tag": "arrival", "focus_template": "First wide view of {subject}"},
        {"shot_type": "medium", "purpose": "retain", "camera_motion": "slow pan",
         "continuity_tag": "enter", "focus_template": "Entering {subject} area"},
    ],
    "reveal": [
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "static tripod",
         "continuity_tag": "context", "focus_template": "Full context of {subject}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "observe", "focus_template": "Observing {feature} at {subject}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "detail", "focus_template": "Detailed look at {feature}"},
    ],
    "explain": [
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "feature_detail", "focus_template": "{feature} detail at {subject}"},
        {"shot_type": "macro", "purpose": "emphasize", "camera_motion": "static macro",
         "continuity_tag": "texture", "focus_template": "Surface texture of {feature}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow push-in",
         "continuity_tag": "understanding", "focus_template": "Understanding {feature} at {subject}"},
    ],
    "discover": [
        {"shot_type": "transition", "purpose": "retain", "camera_motion": "fast whip pan",
         "continuity_tag": "shift", "focus_template": "Shifting perspective on {subject}"},
        {"shot_type": "detail", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "hidden", "focus_template": "Hidden detail of {feature}"},
        {"shot_type": "wide", "purpose": "narrate", "camera_motion": "static tripod",
         "continuity_tag": "reveal_context", "focus_template": "Revealing wider context of {subject}"},
    ],
    "conclude": [
        {"shot_type": "wide", "purpose": "emphasize", "camera_motion": "static tripod",
         "continuity_tag": "final_view", "focus_template": "Final sweeping view of {subject}"},
        {"shot_type": "aerial", "purpose": "conclude", "camera_motion": "drone pullback",
         "continuity_tag": "departure", "focus_template": "Departing from {subject}, pulling back"},
    ],
}

WILDLIFE_NARRATIVE = {
    "hook": [
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "static tripod",
         "continuity_tag": "habitat", "focus_template": "{subject} habitat landscape"},
        {"shot_type": "medium", "purpose": "retain", "camera_motion": "slow pan",
         "continuity_tag": "search", "focus_template": "Searching for {subject} in habitat"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "eyes", "focus_template": "Eyes of {subject} appearing"},
    ],
    "reveal": [
        {"shot_type": "close_up", "purpose": "establish", "camera_motion": "handheld subtle",
         "continuity_tag": "first_sighting", "focus_template": "First clear sighting of {subject}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "behavior", "focus_template": "{subject} in natural behavior"},
        {"shot_type": "macro", "purpose": "emphasize", "camera_motion": "static macro",
         "continuity_tag": "detail_feature", "focus_template": "Distinctive feature of {subject}"},
    ],
    "explain": [
        {"shot_type": "detail", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "adaptation", "focus_template": "{feature} adaptation of {subject}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "environment", "focus_template": "{subject} interacting with environment"},
        {"shot_type": "wide", "purpose": "narrate", "camera_motion": "static tripod",
         "continuity_tag": "ecosystem", "focus_template": "{subject} place in ecosystem"},
    ],
    "discover": [
        {"shot_type": "pov", "purpose": "retain", "camera_motion": "walking handheld",
         "continuity_tag": "tracking", "focus_template": "Tracking {subject} through habitat"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "discovery", "focus_template": "Surprising {subject} behavior revealed"},
        {"shot_type": "transition", "purpose": "narrate", "camera_motion": "fast whip pan",
         "continuity_tag": "reaction", "focus_template": "{subject} reacting to surroundings"},
    ],
    "conclude": [
        {"shot_type": "medium", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "reflection", "focus_template": "Reflecting on {subject} majesty"},
        {"shot_type": "aerial", "purpose": "conclude", "camera_motion": "drone pullback",
         "continuity_tag": "departure", "focus_template": "Aerial departure from {subject} habitat"},
    ],
}

SCIENCE_NARRATIVE = {
    "hook": [
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "slow pan",
         "continuity_tag": "phenomenon", "focus_template": "Natural phenomenon: {feature}"},
        {"shot_type": "medium", "purpose": "retain", "camera_motion": "static tripod",
         "continuity_tag": "question", "focus_template": "Question about {feature}"},
        {"shot_type": "detail", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "focus", "focus_template": "Focusing on {feature} mechanism"},
    ],
    "reveal": [
        {"shot_type": "medium", "purpose": "establish", "camera_motion": "static tripod",
         "continuity_tag": "explanation", "focus_template": "Explaining {feature} of {subject}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "mechanism", "focus_template": "Key mechanism of {feature}"},
        {"shot_type": "macro", "purpose": "emphasize", "camera_motion": "static macro",
         "continuity_tag": "detail", "focus_template": "Micro detail of {feature}"},
    ],
    "explain": [
        {"shot_type": "detail", "purpose": "narrate", "camera_motion": "slow push-in",
         "continuity_tag": "process", "focus_template": "Process of {feature} in {subject}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "static tripod",
         "continuity_tag": "evidence", "focus_template": "Visual evidence of {feature}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "context", "focus_template": "{feature} in real world context"},
    ],
    "discover": [
        {"shot_type": "transition", "purpose": "retain", "camera_motion": "fast whip pan",
         "continuity_tag": "surprise", "focus_template": "Surprising aspect of {feature}"},
        {"shot_type": "wide", "purpose": "narrate", "camera_motion": "static tripod",
         "continuity_tag": "scale", "focus_template": "Scale and impact of {feature}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "implication", "focus_template": "Implication of {feature} for {subject}"},
    ],
    "conclude": [
        {"shot_type": "wide", "purpose": "emphasize", "camera_motion": "slow pan",
         "continuity_tag": "wonder", "focus_template": "Restoring wonder at {feature}"},
        {"shot_type": "aerial", "purpose": "conclude", "camera_motion": "drone pullback",
         "continuity_tag": "perspective", "focus_template": "Big picture perspective on {subject}"},
    ],
}

HISTORY_NARRATIVE = {
    "hook": [
        {"shot_type": "aerial", "purpose": "establish", "camera_motion": "drone flyover",
         "continuity_tag": "ruins", "focus_template": "Aerial of {subject} historical site"},
        {"shot_type": "wide", "purpose": "retain", "camera_motion": "static tripod",
         "continuity_tag": "time_depth", "focus_template": "Sense of time at {subject}"},
        {"shot_type": "detail", "purpose": "emphasize", "camera_motion": "slow push-in",
         "continuity_tag": "ancient_mark", "focus_template": "Ancient markings at {subject}"},
    ],
    "reveal": [
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "architecture", "focus_template": "Architecture of {subject}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "craftsmanship", "focus_template": "Craftsmanship detail at {subject}"},
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "static tripod",
         "continuity_tag": "context", "focus_template": "Historical context of {subject}"},
    ],
    "explain": [
        {"shot_type": "detail", "purpose": "narrate", "camera_motion": "slow push-in",
         "continuity_tag": "artifact", "focus_template": "Artifact detail from {subject} period"},
        {"shot_type": "macro", "purpose": "emphasize", "camera_motion": "static macro",
         "continuity_tag": "texture_age", "focus_template": "Texture of age at {subject}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "story", "focus_template": "Story behind {feature} at {subject}"},
    ],
    "discover": [
        {"shot_type": "transition", "purpose": "retain", "camera_motion": "fast whip pan",
         "continuity_tag": "revelation", "focus_template": "Historical revelation about {subject}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "hidden_detail", "focus_template": "Hidden detail revealing {feature}"},
        {"shot_type": "wide", "purpose": "narrate", "camera_motion": "static tripod",
         "continuity_tag": "legacy", "focus_template": "Legacy of {subject}"},
    ],
    "conclude": [
        {"shot_type": "wide", "purpose": "emphasize", "camera_motion": "slow pan",
         "continuity_tag": "enduring", "focus_template": "{subject} enduring through time"},
        {"shot_type": "aerial", "purpose": "conclude", "camera_motion": "drone pullback",
         "continuity_tag": "farewell", "focus_template": "Farewell to {subject}"},
    ],
}

CULTURAL_NARRATIVE = {
    "hook": [
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "slow pan",
         "continuity_tag": "gathering", "focus_template": "People gathering at {subject}"},
        {"shot_type": "medium", "purpose": "retain", "camera_motion": "handheld subtle",
         "continuity_tag": "participants", "focus_template": "Participants of {feature}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "expression", "focus_template": "Expressions during {feature}"},
    ],
    "reveal": [
        {"shot_type": "detail", "purpose": "establish", "camera_motion": "slow push-in",
         "continuity_tag": "ritual_object", "focus_template": "Ritual object for {feature}"},
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "tradition", "focus_template": "Tradition of {feature} in action"},
        {"shot_type": "macro", "purpose": "emphasize", "camera_motion": "static macro",
         "continuity_tag": "craft", "focus_template": "Craft detail of {feature}"},
    ],
    "explain": [
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "meaning", "focus_template": "Meaning behind {feature}"},
        {"shot_type": "wide", "purpose": "narrate", "camera_motion": "static tripod",
         "continuity_tag": "community", "focus_template": "Community participating in {feature}"},
        {"shot_type": "detail", "purpose": "narrate", "camera_motion": "slow push-in",
         "continuity_tag": "significance", "focus_template": "Significance of {feature}"},
    ],
    "discover": [
        {"shot_type": "pov", "purpose": "retain", "camera_motion": "walking handheld",
         "continuity_tag": "experience", "focus_template": "Experiencing {feature} firsthand"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "emotion", "focus_template": "Emotional moment during {feature}"},
        {"shot_type": "transition", "purpose": "narrate", "camera_motion": "fast whip pan",
         "continuity_tag": "atmosphere", "focus_template": "Atmosphere of {feature}"},
    ],
    "conclude": [
        {"shot_type": "wide", "purpose": "emphasize", "camera_motion": "slow pan",
         "continuity_tag": "legacy", "focus_template": "Legacy of {feature}"},
        {"shot_type": "aerial", "purpose": "conclude", "camera_motion": "drone pullback",
         "continuity_tag": "departure", "focus_template": "Leaving {subject} behind"},
    ],
}

GENERAL_NARRATIVE = {
    "hook": [
        {"shot_type": "wide", "purpose": "establish", "camera_motion": "slow pan",
         "continuity_tag": "context", "focus_template": "Context of {feature}"},
        {"shot_type": "medium", "purpose": "retain", "camera_motion": "static tripod",
         "continuity_tag": "focus", "focus_template": "Focusing on {feature}"},
    ],
    "reveal": [
        {"shot_type": "medium", "purpose": "narrate", "camera_motion": "slow pan",
         "continuity_tag": "explore", "focus_template": "Exploring {feature}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "detail", "focus_template": "Detail of {feature}"},
    ],
    "explain": [
        {"shot_type": "detail", "purpose": "narrate", "camera_motion": "slow push-in",
         "continuity_tag": "examine", "focus_template": "Examining {feature}"},
        {"shot_type": "medium", "purpose": "emphasize", "camera_motion": "static tripod",
         "continuity_tag": "understand", "focus_template": "Understanding {feature}"},
    ],
    "discover": [
        {"shot_type": "transition", "purpose": "retain", "camera_motion": "fast whip pan",
         "continuity_tag": "shift", "focus_template": "New perspective on {feature}"},
        {"shot_type": "close_up", "purpose": "emphasize", "camera_motion": "handheld subtle",
         "continuity_tag": "surprise", "focus_template": "Surprising {feature}"},
    ],
    "conclude": [
        {"shot_type": "wide", "purpose": "emphasize", "camera_motion": "slow pan",
         "continuity_tag": "reflection", "focus_template": "Reflection on {feature}"},
    ],
}

CATEGORY_NARRATIVES: dict[str, dict] = {
    "location": LOCATION_NARRATIVE,
    "wildlife": WILDLIFE_NARRATIVE,
    "science": SCIENCE_NARRATIVE,
    "history": HISTORY_NARRATIVE,
    "cultural": CULTURAL_NARRATIVE,
    "general": GENERAL_NARRATIVE,
}

# ── Duration ranges per category + position ──
CATEGORY_RHYTHM: dict[str, dict[str, dict]] = {
    "location": {
        "hook": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "reveal": {"min": 3.0, "max": 5.0, "energy": "slow"},
        "explain": {"min": 2.5, "max": 4.5, "energy": "medium"},
        "discover": {"min": 1.5, "max": 3.0, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 6.0, "energy": "slow"},
    },
    "wildlife": {
        "hook": {"min": 1.5, "max": 3.0, "energy": "fast"},
        "reveal": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "explain": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "discover": {"min": 1.5, "max": 3.0, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 5.0, "energy": "slow"},
    },
    "science": {
        "hook": {"min": 2.0, "max": 3.5, "energy": "medium"},
        "reveal": {"min": 3.0, "max": 5.0, "energy": "slow"},
        "explain": {"min": 2.5, "max": 4.5, "energy": "medium"},
        "discover": {"min": 2.0, "max": 3.5, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 5.0, "energy": "slow"},
    },
    "history": {
        "hook": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "reveal": {"min": 3.0, "max": 5.0, "energy": "slow"},
        "explain": {"min": 2.5, "max": 4.5, "energy": "medium"},
        "discover": {"min": 2.0, "max": 3.0, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 6.0, "energy": "slow"},
    },
    "cultural": {
        "hook": {"min": 1.5, "max": 3.0, "energy": "fast"},
        "reveal": {"min": 2.5, "max": 4.5, "energy": "medium"},
        "explain": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "discover": {"min": 1.5, "max": 3.0, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 5.0, "energy": "slow"},
    },
    "general": {
        "hook": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "reveal": {"min": 2.5, "max": 4.5, "energy": "medium"},
        "explain": {"min": 2.0, "max": 4.0, "energy": "medium"},
        "discover": {"min": 2.0, "max": 3.5, "energy": "fast"},
        "conclude": {"min": 3.0, "max": 5.0, "energy": "slow"},
    },
}

# ── Location hierarchy for establishing shots ──
LOCATION_HIERARCHY = [
    ("world", "World", ["world map globe", "earth from space", "world geography"]),
    ("country", "India", ["India map", "India geography", "India flag"]),
    ("state", "Maharashtra", ["Maharashtra map", "Maharashtra", "Mumbai skyline"]),
]

# ── B-roll generators per topic domain ──
B_ROLL_TEMPLATES: dict[str, list[str]] = {
    "location": ["landscape view", "road sign", "local life", "aerial view", "map detail"],
    "nature": ["leaves", "water", "birds", "tree branch", "sunlight through trees"],
    "wildlife": ["forest path", "animal tracks", "water source", "tall grass", "morning mist"],
    "historical": ["old architecture", "stone carving", "ancient wall", "stone detail", "old painting"],
    "science": ["microscope", "lab equipment", "data chart", "molecule", "experiment setup"],
    "cultural": ["people gathering", "ritual objects", "traditional dress", "ceremony", "art detail"],
    "temple": ["bell", "oil lamp", "flowers", "incense", "carving detail"],
    "fort": ["stone wall", "gate entrance", "cannon", "view from top", "stairs detail"],
    "lake": ["water surface", "ripples", "shoreline", "reflection", "birds near water"],
    "sky": ["clouds moving", "sun rays", "blue sky", "sunset gradient", "stars night"],
    "tiger": ["forest path", "tiger tracks", "tall grass", "water hole", "jungle path"],
    "general": ["detail texture", "wide landscape", "people walking", "nature scene", "urban life"],
}

B_ROLL_KEYWORD_MAP: dict[str, str] = {
    "tiger": "tiger", "forest": "nature", "jungle": "nature", "lake": "lake",
    "temple": "temple", "fort": "fort", "sky": "sky", "sun": "sky",
    "ocean": "location", "beach": "location", "mountain": "location",
    "village": "cultural", "people": "cultural", "community": "cultural",
    "scientist": "science", "research": "science", "experiment": "science",
    "history": "historical", "king": "historical", "empire": "historical",
    "map": "location", "geography": "location",
}

# ── Hero moment detection patterns ──
HERO_PATTERNS = [
    r"\bthis is\b", r"\bit is\b", r"\bhere\b", r"\bthis (?:fort|temple|lake|place)\b",
    r"\breveal\b", r"\bappear\b", r"\bemerge\b", r"\bshow\b",
    r"\bfirst\b.*\btime\b", r"\bmost\b.*\b(famous|important|beautiful)\b",
    r"\bincredible\b", r"\bamazing\b", r"\bmagnificent\b", r"\bbreathtaking\b",
    r"\benter\b", r"\barrive\b", r"\bwelcome\b",
]

HERO_CLIP_DURATION = 5.0  # Hero shots get longer duration

# ── Subject identity threshold ──
SUBJECT_IDENTITY_THRESHOLD = 60

# ── Search priority weights ──
# Higher = higher priority in entity-first search
SEARCH_PRIORITY = {
    "exact_landmark": 100,
    "exact_subject": 90,
    "nearby_area": 70,
    "same_region": 50,
    "feature_type": 30,
    "generic_context": 10,
}

# ── Subject Identity -> Search Term Mapping ──
# Built dynamically per documentary, but these are default entity hints
DEFAULT_ENTITY_HINTS: dict[str, dict[str, list[str]]] = {
    "raigad": {
        "exact_landmark": ["Raigad Fort", "Raigad Maharashtra"],
        "exact_subject": ["Raigad fort history", "Raigad fort architecture"],
        "nearby_area": ["Mahabaleshwar", "Pune forts", "Konkan forts"],
        "same_region": ["Maharashtra fort", "Maratha empire fort"],
        "feature_type": ["hill fort India", "ancient fort India"],
        "generic_context": ["Indian historical fort", "heritage fort India"],
    },
    "tadoba": {
        "exact_landmark": ["Tadoba Andhari Tiger Reserve", "Tadoba National Park"],
        "exact_subject": ["Tadoba tiger", "Tadoba wildlife"],
        "nearby_area": ["Chandrapur forest", "Vidarbha wildlife"],
        "same_region": ["Maharashtra tiger reserve", "Maharashtra national park"],
        "feature_type": ["tiger reserve India", "national park India"],
        "generic_context": ["Indian wildlife", "wildlife sanctuary India"],
    },
    "lonar": {
        "exact_landmark": ["Lonar Lake", "Lonar crater"],
        "exact_subject": ["Lonar meteorite crater", "Lonar lake Maharashtra"],
        "nearby_area": ["Buldhana district", "Aurangabad"],
        "same_region": ["Maharashtra lake", "Maharashtra crater"],
        "feature_type": ["meteor crater lake", "impact crater India"],
        "generic_context": ["geological wonder India", "unique lake India"],
    },
    "velas": {
        "exact_landmark": ["Velas beach", "Velas village Maharashtra"],
        "exact_subject": ["Velas turtle conservation", "Velas turtle village"],
        "nearby_area": ["Ratnagiri coast", "Dapoli", "Harnai beach"],
        "same_region": ["Maharashtra coastal village", "Konkan village"],
        "feature_type": ["turtle nesting beach India", "turtle conservation India"],
        "generic_context": ["Indian coastal village", "sea turtle conservation"],
    },
    "ants": {
        "exact_landmark": ["ants nature macro", "ant colony close up", "red ants insect"],
        "exact_subject": ["ants teamwork colony", "ants carrying food", "ants working together"],
        "nearby_area": ["ant trail nature", "ant nest ground", "ants insect macro"],
        "same_region": ["ants colony macro", "ant communication", "social insects ants"],
        "feature_type": ["insect behavior ants", "ants teamwork nature", "ant colony documentary"],
        "generic_context": ["nature ants insects", "wildlife ants documentary", "ants nature macro video"],
    },
    "sky": {
        "exact_landmark": ["blue sky", "sky sunlight", "sun rays sky"],
        "exact_subject": ["why sky is blue", "sunlight scattering", "sky color science"],
        "nearby_area": ["atmosphere sunlight", "sunlight through atmosphere", "sky light"],
        "same_region": ["visible light spectrum", "sun rays atmosphere"],
        "feature_type": ["atmospheric phenomenon", "sunlight sky colors"],
        "generic_context": ["nature sky", "beautiful sky clouds", "science nature light"],
    },
}

# ── Camera motion mapping ──
SHOT_TYPE_MOTION: dict[str, str] = {
    "aerial": "drone flyover",
    "wide": "static tripod",
    "medium": "slow pan",
    "close_up": "handheld subtle",
    "macro": "static macro",
    "detail": "slow push-in",
    "transition": "fast whip pan",
    "pov": "walking handheld",
}


# ── Data Models ──

@dataclass
class EnhancedShot:
    """A single shot within a scene."""
    media_type: MediaType
    shot_type: str
    purpose: str
    search_prompt: str
    duration: float
    camera_motion: str = "static"
    visual_focus: str = ""
    is_b_roll: bool = False
    is_establishing: bool = False
    subtitle_label: str = ""
    # Editorial Intelligence fields
    subject_identity_score: float = 0.0
    hero_shot: bool = False
    emotion: str = ""
    continuity_tag: str = ""

    def to_dict(self) -> dict:
        return {
            "media_type": self.media_type.value,
            "shot_type": self.shot_type,
            "purpose": self.purpose,
            "search_prompt": self.search_prompt,
            "duration": round(self.duration, 1),
            "camera_motion": self.camera_motion,
            "visual_focus": self.visual_focus,
            "is_b_roll": self.is_b_roll,
            "is_establishing": self.is_establishing,
            "subtitle_label": self.subtitle_label,
            "subject_identity_score": round(self.subject_identity_score, 1),
            "hero_shot": self.hero_shot,
            "emotion": self.emotion,
            "continuity_tag": self.continuity_tag,
        }


@dataclass
class EnhancedScene:
    """A narrative scene composed of multiple shots."""
    sentence: str
    primary_shots: list[EnhancedShot]
    b_roll_shots: list[EnhancedShot]
    narrative_position: str
    total_duration: float
    emotion: str = ""

    def to_dict(self) -> dict:
        return {
            "sentence": self.sentence,
            "primary_shots": [s.to_dict() for s in self.primary_shots],
            "b_roll_shots": [s.to_dict() for s in self.b_roll_shots],
            "narrative_position": self.narrative_position,
            "total_duration": round(self.total_duration, 1),
            "emotion": self.emotion,
        }


@dataclass
class EnhancedPlan:
    """Complete enhanced production plan."""
    scenes: list[EnhancedScene]
    establishing_shots: list[EnhancedShot]
    script_id: str
    statistics: dict = field(default_factory=dict)
    quality_report: dict = field(default_factory=dict)
    shot_diversity: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenes": [s.to_dict() for s in self.scenes],
            "establishing_shots": [s.to_dict() for s in self.establishing_shots],
            "script_id": self.script_id,
            "statistics": self.statistics,
            "quality_report": self.quality_report,
            "shot_diversity": self.shot_diversity,
        }


# ── Enhanced Planner ──

class EnhancedPlanner:
    """Transforms basic MediaPlans into rich, professionally edited shot sequences."""

    def __init__(self):
        self._shot_counter: dict[str, int] = {st: 0 for st in SHOT_TYPES}
        self._used_assets: list[str] = []
        self._subject_context: dict = {}
        self._category: str = "general"
        self._emotion_arc: list[str] = []
        self._hero_scene_indices: set[int] = set()
        self._continuity_state: dict = {}
        self._search_rotation: int = 0
        self._used_search_prompts: set[str] = set()

    def enhance(
        self,
        plans: list[MediaPlan],
        script: list[dict],
        script_id: str,
    ) -> EnhancedPlan:
        """Main entry point: produce an EnhancedPlan from MediaPlans."""
        self._shot_counter = {st: 0 for st in SHOT_TYPES}
        self._used_assets = []
        self._continuity_state = {}

        # 1. Extract subject identity (name, type, keyword hierarchy)
        self._subject_context = self._extract_subject_identity(plans, script, script_id)

        # 2. Detect documentary category
        self._category = self._detect_category(plans, script_id)

        # 3. Detect emotion arc across all scenes
        self._emotion_arc = self._detect_emotion_arc(script)

        # 4. Detect hero moments
        self._hero_scene_indices = self._detect_hero_moments(script)

        # 5. Detect whether this is a location documentary
        is_location_doc = self._detect_location_doc(plans)

        # 6. Generate establishing shots
        establishing = []
        if is_location_doc:
            establishing = self._build_establishing_shots(plans, script_id)

        # 7. Determine narrative positions for rhythm
        n_scenes = len(plans)
        positions = self._assign_narrative_positions(n_scenes)

        # 8. Expand each plan into editorial shot sequences
        scenes: list[EnhancedScene] = []
        for i, (plan, sentence_data) in enumerate(zip(plans, script)):
            pos = positions[i] if i < len(positions) else "explain"
            emotion = self._emotion_arc[i] if i < len(self._emotion_arc) else ""
            is_hero = i in self._hero_scene_indices
            scene = self._expand_scene_editorial(
                plan, sentence_data, pos, emotion, is_hero, i, n_scenes
            )
            scenes.append(scene)

        # 9. Track diversity and generate report
        diversity = self._compute_diversity()
        quality_report = self._generate_editorial_quality_report(
            scenes, establishing, diversity, plans, script
        )

        # 10. Compile statistics
        total_shots = sum(len(s.primary_shots) + len(s.b_roll_shots) for s in scenes)
        total_shots += len(establishing)
        stats = {
            "total_scenes": len(scenes),
            "total_shots": total_shots,
            "establishing_shots": len(establishing),
            "shot_diversity_score": diversity.get("diversity_score", 0),
            "media_type_distribution": self._media_type_distribution(scenes),
            "category": self._category,
            "hero_scenes": list(self._hero_scene_indices),
            "emotion_arc": self._emotion_arc,
        }

        return EnhancedPlan(
            scenes=scenes,
            establishing_shots=establishing,
            script_id=script_id,
            statistics=stats,
            quality_report=quality_report,
            shot_diversity=diversity,
        )

    # ═══════════════════════════════════════════════
    # SUBJECT IDENTITY ENGINE
    # ═══════════════════════════════════════════════

    def _extract_subject_identity(
        self, plans: list[MediaPlan], script: list[dict], script_id: str
    ) -> dict:
        """Build a subject profile from the script and script_id."""
        subject = script_id or "documentary"
        subject_clean = subject.replace("_", " ").replace("-", " ").title()

        # Collect all nouns and keywords from all plans
        all_keywords: list[str] = []
        for p in plans:
            words = p.search_prompt.split()[:6]
            all_keywords.extend(w.lower() for w in words)
            if p.sentence:
                all_keywords.extend(p.sentence.lower().split()[:8])

        # Count frequency to find dominant subject terms
        counts = Counter(all_keywords)
        stop_words = {"the", "a", "an", "in", "of", "to", "is", "and", "it",
                      "this", "that", "for", "with", "on", "at", "by", "from",
                      "map", "geography", "world", "topography", "india"}
        top_terms = [w for w, _ in counts.most_common(15)
                     if w not in stop_words and len(w) > 2][:5]

        # Build entity-first search hierarchy
        entity_hints = DEFAULT_ENTITY_HINTS.get(script_id, {})

        # If no entity hints, generate from subject + top terms
        if not entity_hints:
            entity_hints = self._build_entity_hints(subject, subject_clean, top_terms, script)

        # Extract location levels for establishing shots
        location_levels = self._extract_location_levels(subject, subject_clean, script)

        return {
            "subject": subject,
            "subject_clean": subject_clean,
            "top_terms": top_terms,
            "entity_hints": entity_hints,
            "location_levels": location_levels,
        }

    def _build_entity_hints(
        self, subject: str, subject_clean: str, top_terms: list[str], script: list[dict]
    ) -> dict:
        """Generate entity search hierarchy from available context."""
        subject_q = subject_clean
        term_str = " ".join(top_terms[:3]) if top_terms else subject_q

        hints = {
            "exact_landmark": [f"{subject_q}", f"{subject_q} India"],
            "exact_subject": [f"{subject_q} {term_str}", f"{subject_q} documentary"],
            "nearby_area": [f"{term_str} region", f"{term_str} area"],
            "same_region": [f"{subject_q} Maharashtra", f"Maharashtra {top_terms[0] if top_terms else ''}"],
            "feature_type": [term_str],
            "generic_context": [f"{top_terms[0] if top_terms else 'nature'} documentary"],
        }
        return hints

    def _extract_location_levels(
        self, subject: str, subject_clean: str, script: list[dict]
    ) -> dict:
        """Extract geographic hierarchy from script content."""
        return {
            "subject": subject_clean,
            "queries": [f"{subject_clean}", f"{subject_clean} aerial view",
                        f"{subject_clean} landscape"],
        }

    def _score_subject_identity(self, prompt: str, shot_type: str, purpose: str) -> float:
        """Score how well a shot represents the documentary subject. 0-100."""
        prompt_lower = prompt.lower()
        subject = self._subject_context.get("subject_clean", "").lower()
        top_terms = self._subject_context.get("top_terms", [])
        entity_hints = self._subject_context.get("entity_hints", {})

        # Collect all subject-related terms
        subject_terms: list[str] = [subject]
        for level in ["exact_landmark", "exact_subject", "nearby_area", "same_region"]:
            for hint in entity_hints.get(level, []):
                subject_terms.extend(hint.lower().split()[:4])
        subject_terms.extend(top_terms)
        subject_terms = list(set(t.lower() for t in subject_terms if len(t) > 2))

        # Score based on term overlap
        if not subject_terms:
            return 50.0

        matches = sum(1 for term in subject_terms if term in prompt_lower)
        overlap = matches / max(len(subject_terms) * 0.3, 1)  # Normalize

        # Bonus for exact subject match
        bonus = 0
        if subject in prompt_lower:
            bonus = 20

        # Penalty for generic-only content
        penalty = 0
        generic_indicators = ["stock", "footage", "generic", "background", "texture"]
        if any(g in prompt_lower for g in generic_indicators):
            penalty = 30

        raw = min(100, overlap * 100 + bonus - penalty)
        return max(0, raw)

    def _is_shot_relevant(self, prompt: str, shot_type: str, purpose: str) -> bool:
        """Check if shot passes subject identity threshold."""
        score = self._score_subject_identity(prompt, shot_type, purpose)
        return score >= SUBJECT_IDENTITY_THRESHOLD

    # ═══════════════════════════════════════════════
    # CATEGORY DETECTION
    # ═══════════════════════════════════════════════

    def _detect_category(self, plans: list[MediaPlan], script_id: str) -> str:
        """Detect documentary category from plans and script_id."""
        # Check if there's a known entity for this script_id
        if script_id in DEFAULT_ENTITY_HINTS:
            # Map script_id to category
            if script_id in ("raigad", "lonar", "velas"):
                return "location"
            if script_id == "tadoba":
                return "wildlife"
            if script_id == "sky":
                return "science"
            if script_id == "ants":
                return "science"  # Ant collective intelligence = science doc

        # Count media types
        media_counts: dict[str, int] = {}
        keyword_counts: dict[str, int] = {}
        for p in plans:
            mt = p.media_type.value
            media_counts[mt] = media_counts.get(mt, 0) + 1
            if p.sentence:
                lower = p.sentence.lower()
                for cat, keywords in CATEGORY_KEYWORDS.items():
                    for kw in keywords:
                        if kw in lower:
                            keyword_counts[cat] = keyword_counts.get(cat, 0) + 1

        # Check media type signals
        if media_counts.get("map", 0) >= 2:
            return "location"
        if media_counts.get("scientific_animation", 0) >= 1:
            return "science"

        # Check keyword signals
        if keyword_counts:
            best = max(keyword_counts, key=keyword_counts.get)
            return best if best in EDITORIAL_CATEGORIES else "general"

        return "general"

    def _detect_location_doc(self, plans: list[MediaPlan]) -> bool:
        """Check if this documentary has geographic location content.
        Also triggers for named places regardless of category (e.g., Tadoba is
        wildlife but also a named location that needs establishing shots).
        Science-category scripts (e.g., 'ants', 'sky') never get establishing shots."""
        if self._category == "location":
            return True
        if self._category == "science":
            return False
        # Check if script_id maps to a known entity with location hints
        if self._subject_context.get("subject_clean", "").lower() in DEFAULT_ENTITY_HINTS:
            return True
        # Check for named place patterns in sentences
        named_place_count = sum(1 for p in plans if p.media_type == MediaType.MAP)
        if named_place_count >= 1:
            return True
        location_keywords = ["fort", "lake", "temple", "mountain", "river", "village",
                             "city", "park", "reserve", "sanctuary", "coast", "beach"]
        for p in plans:
            if p.sentence:
                lower = p.sentence.lower()
                if any(kw in lower for kw in location_keywords):
                    return True
        return False

    # ═══════════════════════════════════════════════
    # ESTABLISHING SHOTS
    # ═══════════════════════════════════════════════

    def _build_establishing_shots(
        self, plans: list[MediaPlan], script_id: str
    ) -> list[EnhancedShot]:
        """Build a 3-4 shot map zoom-in sequence for location docs."""
        location_keywords = self._extract_location_keywords(plans)
        shots = []
        duration_per_shot = 2.5

        # Non-location docs (e.g., Tadoba wildlife) skip world/country/state
        if self._category == "location":
            levels = LOCATION_HIERARCHY + [
                ("subject", location_keywords["subject"], location_keywords["queries"])
            ]
        else:
            levels = [
                ("subject", location_keywords["subject"], location_keywords["queries"])
            ]

        for level_name, label, queries in levels:
            if level_name == "subject" and not queries:
                continue
            p = self._entity_first_search(
                label, level_name, queries, "aerial" if level_name in ("world", "subject") else "wide"
            )
            shot = EnhancedShot(
                media_type=MediaType.MAP,
                shot_type="aerial" if level_name in ("world", "subject") else "wide",
                purpose="establish",
                search_prompt=p,
                duration=duration_per_shot,
                camera_motion="drone flyover" if level_name == "subject" else "static",
                visual_focus=f"Geographic location: {label}",
                is_establishing=True,
                subtitle_label=label,
                subject_identity_score=100.0,
                emotion="curiosity",
                continuity_tag=f"zoom_to_{level_name}",
            )
            shots.append(shot)
            self._track_shot(shot)

        return shots

    def _extract_location_keywords(self, plans: list[MediaPlan]) -> dict:
        """Extract location keywords from plans for establishing shots."""
        subject_keywords = []
        for p in plans:
            if p.sentence:
                words = p.search_prompt.split()[:3]
                subject_keywords.extend(words)
        counts = Counter(subject_keywords)
        top = [w for w, _ in counts.most_common(5) if w.lower() not in
               {"map", "geography", "world", "topography", "india", "the", "a"}]
        subject = top[0] if top else "fort"
        queries = [
            f"{subject} India",
            f"{subject} landscape",
            f"{subject} aerial view",
        ]
        return {"subject": subject, "queries": queries}

    # ═══════════════════════════════════════════════
    # EMOTIONAL STORYTELLING
    # ═══════════════════════════════════════════════

    def _detect_emotion_arc(self, script: list[dict]) -> list[str]:
        """Detect the emotional tone of each scene."""
        emotions = []
        for s in script:
            text = (s.get("hi", "") + " " + s.get("en", "")).lower()
            emotion = self._detect_emotion(text)
            emotions.append(emotion)
        return emotions

    def _detect_emotion(self, text: str) -> str:
        """Classify emotional tone of a sentence. Returns emotion label."""
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[emotion] = score
        if not scores:
            return "curiosity"  # Default: learning-focused
        return max(scores, key=scores.get)

    def _emotion_visual_motif(self, emotion: str, default: list[str] = None) -> str:
        """Get a visual motif for the emotion."""
        motifs = EMOTION_VISUAL_MOTIFS.get(emotion, EMOTION_VISUAL_MOTIFS.get("curiosity", []))
        if not motifs:
            return ""
        return random.choice(motifs)

    # ═══════════════════════════════════════════════
    # HERO MOMENT DETECTION
    # ═══════════════════════════════════════════════

    def _detect_hero_moments(self, script: list[dict]) -> set[int]:
        """Detect which scenes should have hero treatment."""
        import re
        hero_indices: set[int] = set()

        for i, s in enumerate(script):
            text = (s.get("hi", "") + " " + s.get("en", "")).lower()
            score = 0

            # Check hero patterns
            for pattern in HERO_PATTERNS:
                if re.search(pattern, text):
                    score += 1

            # First scene that names the subject is a hero moment
            subject_lower = self._subject_context.get("subject_clean", "").lower()
            if subject_lower and subject_lower in text:
                score += 2

            # Sentences with strong emotional language
            for emotion, keywords in EMOTION_KEYWORDS.items():
                if emotion in ("awe", "wonder", "fear"):
                    if any(kw in text for kw in keywords):
                        score += 1

            if score >= 2:
                hero_indices.add(i)

        # Ensure at least 1 hero if script is long enough, at most 3
        if len(script) >= 3 and not hero_indices:
            # Default: first establishing scene or middle scene
            hero_indices.add(0)
        if len(hero_indices) > 3:
            # Keep highest-scored
            hero_indices = set(list(hero_indices)[:3])

        return hero_indices

    # ═══════════════════════════════════════════════
    # NARRATIVE POSITIONS
    # ═══════════════════════════════════════════════

    def _assign_narrative_positions(self, n: int) -> list[str]:
        """Assign rhythmic positions across the documentary."""
        if n <= 1:
            return ["explain"]
        if n == 2:
            return ["hook", "conclude"]
        if n == 3:
            return ["hook", "explain", "conclude"]

        positions = ["hook"]
        middle = n - 2
        pattern = ["reveal", "explain", "discover"] * (middle // 3 + 1)
        positions.extend(pattern[:middle])
        positions.append("conclude")
        return positions[:n]

    # ═══════════════════════════════════════════════
    # EDITORIAL SCENE EXPANSION
    # ═══════════════════════════════════════════════

    def _expand_scene_editorial(
        self,
        plan: MediaPlan,
        sentence_data: dict,
        position: str,
        emotion: str,
        is_hero: bool,
        scene_idx: int,
        total_scenes: int,
    ) -> EnhancedScene:
        """Expand a scene using editorial intelligence: narrative sequence, continuity, emotion."""
        media_type_str = plan.media_type.value

        # Get category-specific narrative template
        narratives = CATEGORY_NARRATIVES.get(self._category, GENERAL_NARRATIVE)
        beats = narratives.get(position, narratives.get("explain", []))

        # Adjust beat count based on hero status
        if is_hero:
            beats = beats[:3]  # Hero moments get full 3-shot treatment
        else:
            beats = beats[:2] if len(beats) > 2 else beats  # Non-hero: 2 shots

        # Get category-specific rhythm
        cat_rhythm = CATEGORY_RHYTHM.get(self._category, CATEGORY_RHYTHM["general"])
        rhythm = cat_rhythm.get(position, cat_rhythm.get("explain", {"min": 2.0, "max": 4.0, "energy": "medium"}))

        # Get subject and feature context
        subject = self._subject_context.get("subject_clean", "")
        en_text = sentence_data.get("en", plan.sentence)
        feature_words = en_text.split()[:3]
        feature = " ".join(feature_words) if feature_words else subject

        # Build primary shots from narrative beats
        primary: list[EnhancedShot] = []
        for j, beat in enumerate(beats):
            # Entity-first search for the search prompt
            focus = beat["focus_template"].format(subject=subject, feature=feature)
            search_prompt = self._entity_first_search(
                focus, beat["shot_type"], [focus],
                beat["shot_type"]
            )

            # Duration: hero shots get extended duration
            if is_hero:
                duration = HERO_CLIP_DURATION
            elif len(beats) == 1:
                duration = max(rhythm["min"], (rhythm["min"] + rhythm["max"]) / 2)
            else:
                duration = round(random.uniform(rhythm["min"], rhythm["max"]), 1)

            # Subject identity score
            identity_score = self._score_subject_identity(search_prompt, beat["shot_type"], beat["purpose"])

            # If subject identity is too low, fall back to entity-first search
            if identity_score < SUBJECT_IDENTITY_THRESHOLD:
                fallback = self._entity_first_search(
                    subject, beat["shot_type"],
                    [f"{subject} {beat['shot_type']}", f"{subject} documentary"],
                    beat["shot_type"]
                )
                search_prompt = fallback
                identity_score = self._score_subject_identity(search_prompt, beat["shot_type"], beat["purpose"])

            camera = beat.get("camera_motion", SHOT_TYPE_MOTION.get(beat["shot_type"], "static"))

            # Add emotion visual motif to visual focus
            emotion_motif = self._emotion_visual_motif(emotion)
            vis_focus = focus
            if emotion_motif and is_hero:
                vis_focus = f"{focus} — {emotion_motif}"

            shot = EnhancedShot(
                media_type=plan.media_type,
                shot_type=beat["shot_type"],
                purpose=beat["purpose"],
                search_prompt=search_prompt,
                duration=duration,
                camera_motion=camera,
                visual_focus=vis_focus,
                is_b_roll=False,
                is_establishing=False,
                subject_identity_score=identity_score,
                hero_shot=is_hero,
                emotion=emotion,
                continuity_tag=beat["continuity_tag"],
            )
            primary.append(shot)
            self._track_shot(shot)

        # Generate emotion-aligned B-roll
        b_roll = self._interleave_b_roll_for_emotion(
            plan.search_prompt, sentence_data, emotion, is_hero
        )

        total_dur = sum(s.duration for s in primary) + sum(s.duration for s in b_roll)

        return EnhancedScene(
            sentence=sentence_data.get("hi", "") or sentence_data.get("en", ""),
            primary_shots=primary,
            b_roll_shots=b_roll,
            narrative_position=position,
            total_duration=total_dur,
            emotion=emotion,
        )

    # ═══════════════════════════════════════════════
    # ENTITY-FIRST SEARCH
    # ═══════════════════════════════════════════════

    def _entity_first_search(
        self, base_prompt: str, shot_type: str,
        specific_queries: list[str] = None,
        preferred_type: str = None,
    ) -> str:
        """
        Build a search prompt using entity-first hierarchy.
        Exact landmark → exact subject → nearby → region → feature → generic.
        """
        entity_hints = self._subject_context.get("entity_hints", {})
        subject = self._subject_context.get("subject_clean", "")

        # Priority queue of search candidates
        candidates: list[tuple[int, str]] = []

        # 1. Exact landmark level (highest priority)
        for hint in entity_hints.get("exact_landmark", []):
            candidates.append((SEARCH_PRIORITY["exact_landmark"], hint))

        # 2. Specific queries (if provided)
        if specific_queries:
            for q in specific_queries:
                candidates.append((SEARCH_PRIORITY["exact_subject"], q))

        # 3. Exact subject level
        for hint in entity_hints.get("exact_subject", []):
            candidates.append((SEARCH_PRIORITY["exact_subject"], hint))

        # 4. Shot-type modifier on subject
        if subject:
            candidates.append((SEARCH_PRIORITY["nearby_area"], f"{subject} {shot_type}"))
            candidates.append((SEARCH_PRIORITY["nearby_area"], f"{shot_type} {subject}"))

        # 5. Nearby area
        for hint in entity_hints.get("nearby_area", []):
            candidates.append((SEARCH_PRIORITY["nearby_area"], hint))

        # 6. Same region
        for hint in entity_hints.get("same_region", []):
            candidates.append((SEARCH_PRIORITY["same_region"], hint))

        # 7. Feature type
        for hint in entity_hints.get("feature_type", []):
            candidates.append((SEARCH_PRIORITY["feature_type"], hint))

        # 8. Generic context (lowest priority)
        for hint in entity_hints.get("generic_context", []):
            candidates.append((SEARCH_PRIORITY["generic_context"], hint))

        # 9. Original base prompt as last resort
        candidates.append((0, base_prompt))

        # Deduplicate and sort by priority
        seen = set()
        unique_candidates: list[tuple[int, str]] = []
        for pri, prompt in candidates:
            lower = prompt.lower().strip()
            if lower not in seen:
                seen.add(lower)
                unique_candidates.append((pri, prompt))

        unique_candidates.sort(key=lambda x: -x[0])

        if not unique_candidates:
            return base_prompt

        # Track which prompts have been returned by this instance.
        # Advance through the candidate list (wrapping around) until we
        # find one that hasn't been used yet, or until we've scanned
        # the entire list once.  This guarantees fresh prompts while
        # preferring high-priority entries.
        total = len(unique_candidates)
        for offset in range(total):
            idx = (self._search_rotation + offset) % total
            pri, prompt = unique_candidates[idx]
            key = prompt.strip().lower()
            if key and key not in self._used_search_prompts:
                self._used_search_prompts.add(key)
                self._search_rotation = (idx + 1) % total
                return prompt.strip()

        # All prompts exhausted — cycle from where we left off
        idx = self._search_rotation % total
        self._search_rotation = (idx + 1) % total
        return unique_candidates[idx][1].strip()

    # ═══════════════════════════════════════════════
    # EMOTIONAL B-ROLL
    # ═══════════════════════════════════════════════

    def _interleave_b_roll_for_emotion(
        self, search_prompt: str, sentence_data: dict,
        emotion: str, is_hero: bool
    ) -> list[EnhancedShot]:
        """Generate B-roll that reinforces the emotional tone of the scene."""
        en_text = sentence_data.get("en", "").lower()
        domain = "general"
        sentence_text = en_text + " " + search_prompt.lower()
        for keyword, dom in B_ROLL_KEYWORD_MAP.items():
            if keyword in sentence_text:
                domain = dom
                break

        templates = B_ROLL_TEMPLATES.get(domain, B_ROLL_TEMPLATES["general"])

        # For hero scenes, use emotion-aligned B-roll instead of generic
        if is_hero and emotion:
            emotion_motifs = EMOTION_VISUAL_MOTIFS.get(emotion, [])
            if emotion_motifs:
                templates = emotion_motifs + templates

        # Pick 1 B-roll shot (2 for hero)
        n_broll = 2 if is_hero else 1
        selected = random.sample(templates, min(n_broll, len(templates)))

        b_roll = []
        subject = self._subject_context.get("subject_clean", "")
        for k, br_template in enumerate(selected):
            # Entity-first search for B-roll prompt
            br_prompt = self._entity_first_search(
                br_template, "detail",
                [f"{subject} {br_template}", br_template],
                "detail"
            )
            br_shot = EnhancedShot(
                media_type=MediaType.STOCK_VIDEO,
                shot_type=random.choice(["detail", "close_up", "macro"]),
                purpose="b_roll",
                search_prompt=br_prompt,
                duration=2.5 if is_hero else 1.8,
                camera_motion="static handheld",
                visual_focus=f"{emotion}: {br_template}" if emotion else br_template,
                is_b_roll=True,
                subject_identity_score=self._score_subject_identity(br_prompt, "detail", "b_roll"),
                emotion=emotion,
                continuity_tag="b_roll_mood",
            )
            b_roll.append(br_shot)
            self._track_shot(br_shot)

        return b_roll

    # ═══════════════════════════════════════════════
    # SHOT TRACKING
    # ═══════════════════════════════════════════════

    def _track_shot(self, shot: EnhancedShot):
        """Track shot type for diversity scoring."""
        self._shot_counter[shot.shot_type] = (
            self._shot_counter.get(shot.shot_type, 0) + 1
        )
        self._used_assets.append(shot.search_prompt)

    # ═══════════════════════════════════════════════
    # DIVERSITY COMPUTATION
    # ═══════════════════════════════════════════════

    def _compute_diversity(self) -> dict:
        """Compute shot diversity score (0-100)."""
        total = sum(self._shot_counter.values())
        if total == 0:
            return {"diversity_score": 0, "shot_counts": {}}

        n_types = len([v for v in self._shot_counter.values() if v > 0])
        if n_types <= 1:
            return {"diversity_score": 0, "shot_counts": dict(self._shot_counter)}

        ideal_per_type = total / n_types
        variance = sum(
            (v - ideal_per_type) ** 2 for v in self._shot_counter.values()
        ) / n_types
        max_variance = (total - ideal_per_type) ** 2
        score = max(0, 100 - (variance / max(max_variance, 1)) * 100)

        asset_repeat_pct = 0
        if self._used_assets:
            unique = len(set(self._used_assets))
            asset_repeat_pct = (1 - unique / len(self._used_assets)) * 100

        return {
            "diversity_score": round(score, 1),
            "shot_counts": dict(self._shot_counter),
            "n_shot_types_used": n_types,
            "total_shots": total,
            "asset_repeat_pct": round(asset_repeat_pct, 1),
        }

    def _media_type_distribution(self, scenes: list[EnhancedScene]) -> dict:
        """Compute media type distribution across all shots."""
        counts = {}
        for scene in scenes:
            for shot in scene.primary_shots + scene.b_roll_shots:
                mt = shot.media_type.value
                counts[mt] = counts.get(mt, 0) + 1
        total = sum(counts.values()) or 1
        return {k: round(v / total * 100, 1) for k, v in counts.items()}

    # ═══════════════════════════════════════════════
    # ENHANCED QUALITY GATE
    # ═══════════════════════════════════════════════

    def _generate_editorial_quality_report(
        self,
        scenes: list[EnhancedScene],
        establishing: list[EnhancedShot],
        diversity: dict,
        plans: list[MediaPlan],
        script: list[dict],
    ) -> dict:
        """Generate comprehensive editorial quality assessment with 12 dimensions."""
        total_shots = sum(
            len(s.primary_shots) + len(s.b_roll_shots) for s in scenes
        ) + len(establishing)

        # ── 1. Subject Identity Score ──
        all_shots = []
        for s in scenes:
            all_shots.extend(s.primary_shots)
            all_shots.extend(s.b_roll_shots)
        all_shots.extend(establishing)

        if all_shots:
            avg_identity = sum(s.subject_identity_score for s in all_shots) / len(all_shots)
            # Count shots above threshold
            above_threshold = sum(1 for s in all_shots if s.subject_identity_score >= SUBJECT_IDENTITY_THRESHOLD)
            identity_percentage = above_threshold / len(all_shots) * 100
            subject_identity_score = min(100, avg_identity * 0.6 + identity_percentage * 0.4)
        else:
            subject_identity_score = 0

        # ── 2. Storytelling Score ──
        # Do we have narrative shot sequences (continuity tags change naturally)?
        if scenes:
            continuity_chains = sum(
                1 for s in scenes if len(s.primary_shots) >= 2
            )
            storytelling_score = min(100, continuity_chains / max(len(scenes), 1) * 100)
        else:
            storytelling_score = 0

        # ── 3. Shot Continuity Score ──
        # Do consecutive shots within a scene have different continuity tags?
        continuity_score = 0
        total_pairs = 0
        for s in scenes:
            for j in range(len(s.primary_shots) - 1):
                total_pairs += 1
                if s.primary_shots[j].continuity_tag != s.primary_shots[j + 1].continuity_tag:
                    continuity_score += 1
        if total_pairs > 0:
            continuity_score = continuity_score / total_pairs * 100

        # ── 4. Visual Diversity Score ──
        div_score = diversity.get("diversity_score", 0)

        # ── 5. Educational Clarity Score ──
        # Uses correct media types for the content
        has_map = any(s.media_type == MediaType.MAP for s in plans)
        has_infographic = any(s.media_type == MediaType.INFOGRAPHIC for s in plans)
        has_sci_anim = any(s.media_type == MediaType.SCIENTIFIC_ANIMATION for s in plans)
        educational_score = 50
        if self._category == "science" and (has_sci_anim or has_infographic):
            educational_score = 100
        elif self._category == "location" and has_map:
            educational_score = 100
        elif self._category == "wildlife":
            educational_score = 80  # Wildlife prefers real footage, not infographics

        # ── 6. Hero Moments Score ──
        hero_count = len(self._hero_scene_indices)
        hero_shot_count = sum(
            1 for s in scenes for p in s.primary_shots if p.hero_shot
        )
        if hero_count >= 1 and hero_shot_count >= hero_count:
            hero_score = 100
        elif hero_count >= 1:
            hero_score = 60
        else:
            hero_score = 0

        # ── 7. Narrative Flow Score ──
        # Positions should vary
        positions_used = set(s.narrative_position for s in scenes)
        rhythm_variety = len(positions_used)
        if rhythm_variety >= 3:
            flow_score = 100
        elif rhythm_variety >= 2:
            flow_score = 60
        else:
            flow_score = 30

        # ── 8. Retention Prediction Score ──
        # Built from: emotion variety + hero moments + shot diversity + pacing
        emotion_variety = len(set(s.emotion for s in scenes if s.emotion))
        retention_score = min(100, (
            (rhythm_variety / 5 * 25) +
            (hero_score / 100 * 25) +
            (div_score / 100 * 25) +
            (min(emotion_variety * 20, 100) * 0.25)
        ))

        # ── 9. Establishing Shots Score ──
        has_establishing = len(establishing) >= 2
        establishing_score = 100 if has_establishing else 0

        # ── 10. B-Roll Usage Score ──
        b_roll_count = sum(len(s.b_roll_shots) for s in scenes)
        if b_roll_count >= len(scenes) * 0.3:
            b_roll_score = 100
        elif b_roll_count > 0:
            b_roll_score = 60
        else:
            b_roll_score = 0

        # ── 11. Visual Density Score ──
        if total_shots >= len(scenes) * 2:
            density_score = 100
        else:
            density_score = 50

        # ── 12. Emotion Alignment Score ──
        emotion_scenes = sum(1 for s in scenes if s.emotion)
        if emotion_scenes >= len(scenes) * 0.7:
            emotion_score = 100
        elif emotion_scenes > 0:
            emotion_score = 60
        else:
            emotion_score = 0

        # ── Compile component scores ──
        component_scores = [
            ("Subject Identity", round(subject_identity_score, 1)),
            ("Storytelling", round(storytelling_score, 1)),
            ("Shot Continuity", round(continuity_score, 1)),
            ("Visual Diversity", round(div_score, 1)),
            ("Educational Clarity", round(educational_score, 1)),
            ("Hero Moments", round(hero_score, 1)),
            ("Narrative Flow", round(flow_score, 1)),
            ("Retention Prediction", round(retention_score, 1)),
            ("Establishing Shots", round(establishing_score, 1)),
            ("B-Roll Usage", round(b_roll_score, 1)),
            ("Visual Density", round(density_score, 1)),
            ("Emotion Alignment", round(emotion_score, 1)),
        ]

        overall = round(sum(s[1] for s in component_scores) / len(component_scores), 1)

        # ── Weakness detection ──
        weaknesses = []
        for name, score in component_scores:
            if score < 60:
                weaknesses.append({
                    "dimension": name,
                    "score": score,
                    "severity": "critical" if score < 30 else "warning",
                })

        checks = {
            "has_establishing_shots": has_establishing,
            "has_map_for_location": has_map,
            "has_infographic_for_data": has_infographic,
            "has_scientific_animation_for_science": has_sci_anim,
            "b_roll_scenes": b_roll_count,
            "shot_diversity_score": div_score,
            "rhythm_positions_used": list(positions_used),
            "rhythm_variety": rhythm_variety,
            "total_shots": total_shots,
            "total_scenes": len(scenes),
            "subject_identity_avg": round(avg_identity, 1) if all_shots else 0,
            "identity_above_threshold": round(identity_percentage, 1) if all_shots else 0,
            "hero_moments_detected": list(self._hero_scene_indices),
            "emotion_arc": self._emotion_arc,
            "category": self._category,
            "weaknesses": weaknesses,
        }

        return {
            "overall_quality_score": overall,
            "component_scores": component_scores,
            "checks": checks,
        }
