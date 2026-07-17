import random
from dataclasses import dataclass, field


@dataclass
class VisualStorytelling:
    emotion: str = "Wonder"
    camera_style: str = "Cinematic"
    camera_movement: str = "Slow Push"
    transition: str = "Crossfade"
    focus_subject: str = ""
    secondary_subject: str = ""
    background_atmosphere: str = ""
    lighting: str = "Natural"
    color_palette: str = "Warm"
    tempo: str = "Gentle"  # Gentle, Moderate, Dynamic


CAMERA_STYLES = [
    "Cinematic", "Drone", "Wide", "Close-up", "Macro",
    "Aerial", "Tracking", "Underground", "Overhead", "POV",
]

CAMERA_MOVEMENTS = [
    "Slow Push", "Slow Pull", "Tracking Left", "Tracking Right",
    "Crane Up", "Crane Down", "Static", "Orbit", "Pan",
]

EMOTIONS = [
    "Mystery", "Wonder", "Amazement", "Curiosity", "Reflection",
    "Hope", "Surprise", "Calm", "Awe", "Nostalgia", "Tension",
]

LIGHTING = [
    "Golden Hour", "Natural", "Dramatic", "Soft", "Hard",
    "Backlit", "Silhouette", "Twilight", "Overcast", "Moonlight",
]

ATMOSPHERES = [
    "Misty forest", "Open sky", "Dense canopy", "Underground darkness",
    "Sunlit clearing", "Urban bustle", "Tranquil water", "Mountain air",
    "Desert heat", "Tropical humidity",
]

COLOR_PALETTES = [
    "Warm", "Cool", "Natural", "Muted", "Vibrant",
    "Monochrome", "Earth tones", "Pastel", "High contrast",
]

TRANSITIONS = [
    "Crossfade", "Dissolve", "Fade to Black", "Match Cut",
    "Wipe", "Swipe", "Push", "Zoom",
]

TEMPOS = ["Gentle", "Moderate", "Dynamic"]

FOCUS_THEMES: dict[str, list[str]] = {
    "forest": ["Tree canopy", "Forest floor", "Root system", "Foliage detail"],
    "temple": ["Temple spire", "Stone carvings", "Inner sanctum", "Pillars"],
    "village": ["Village houses", "Streets", "People", "Courtyard"],
    "mountain": ["Peak", "Ridge line", "Snow cap", "Valley below"],
    "river": ["Water surface", "River bend", "Shoreline", "Rapids"],
    "city": ["Skyline", "Street level", "Architecture", "Traffic"],
    "ocean": ["Wave pattern", "Horizon", "Coastline", "Deep water"],
    "desert": ["Dune curve", "Sand texture", "Horizon", "Oasis"],
    "default": ["Main subject", "Context view", "Detail shot", "Wide establishing"],
}


class SceneDirector:
    @staticmethod
    def direct(narration: str, visual_goal: str = "", shot_type: str = "") -> VisualStorytelling:
        combined = (narration + " " + visual_goal).lower()

        emotion = SceneDirector._pick_emotion(combined)
        camera = SceneDirector._pick_camera(combined, shot_type)
        movement = SceneDirector._pick_movement(emotion, camera)
        lighting = SceneDirector._pick_lighting(emotion, combined)
        atmosphere = SceneDirector._pick_atmosphere(combined)
        palette = SceneDirector._pick_palette(emotion)
        subjects = SceneDirector._pick_subjects(combined)
        tempo = SceneDirector._pick_tempo(emotion)

        return VisualStorytelling(
            emotion=emotion,
            camera_style=camera,
            camera_movement=movement,
            transition=random.choice(TRANSITIONS),
            focus_subject=subjects[0],
            secondary_subject=subjects[1] if len(subjects) > 1 else "",
            background_atmosphere=atmosphere,
            lighting=lighting,
            color_palette=palette,
            tempo=tempo,
        )

    @staticmethod
    def _pick_emotion(text: str) -> str:
        if any(w in text for w in ["रहस्य", "mystery", "अनजान", "unknown", "हैरान"]):
            return "Mystery"
        if any(w in text for w in ["आश्चर्य", "amazing", "अद्भुत", "incredible", "wonder"]):
            return "Wonder"
        if any(w in text for w in ["खोज", "discover", "discovery", "वैज्ञानिक", "scientist"]):
            return "Curiosity"
        if any(w in text for w in ["डर", "fear", "खतरा", "danger", "warning"]):
            return "Tension"
        if any(w in text for w in ["सुंदर", "beautiful", "शांत", "peaceful", "calm"]):
            return "Calm"
        return random.choice(EMOTIONS)

    @staticmethod
    def _pick_camera(text: str, shot_type: str) -> str:
        if shot_type:
            style_map = {
                "drone": "Drone", "aerial": "Aerial", "wide": "Wide",
                "close-up": "Close-up", "macro": "Macro", "tracking": "Tracking",
                "cinematic": "Cinematic", "underground": "Underground",
            }
            return style_map.get(shot_type, "Cinematic")
        if any(w in text for w in ["ऊपर", "aerial", "drone", "हवाई", "bird"]):
            return "Drone"
        if any(w in text for w in ["पास", "close", "डिटेल", "detail", "बारीक"]):
            return "Close-up"
        if any(w in text for w in ["अंदर", "inside", "under", "below", "भीतर"]):
            return "Underground"
        return random.choice(CAMERA_STYLES)

    @staticmethod
    def _pick_movement(emotion: str, camera: str) -> str:
        if camera in ("Drone", "Aerial"):
            return random.choice(["Tracking Left", "Tracking Right", "Slow Push", "Pan"])
        if emotion in ("Calm", "Wonder", "Nostalgia"):
            return random.choice(["Slow Push", "Slow Pull", "Static"])
        if emotion in ("Tension", "Surprise", "Dynamic"):
            return random.choice(["Orbit", "Crane Up", "Tracking Left", "Push"])
        return random.choice(CAMERA_MOVEMENTS)

    @staticmethod
    def _pick_lighting(emotion: str, text: str) -> str:
        if "sunset" in text or "सूर्यास्त" in text or "शाम" in text:
            return "Golden Hour"
        if "रात" in text or "night" in text or "चाँद" in text:
            return "Moonlight"
        if "नाटकीय" in text or "dramatic" in text or "drama" in text:
            return "Dramatic"
        if emotion in ("Mystery", "Tension"):
            return random.choice(["Dramatic", "Silhouette", "Twilight"])
        if emotion in ("Calm", "Wonder", "Nostalgia"):
            return random.choice(["Golden Hour", "Soft", "Natural"])
        return random.choice(LIGHTING)

    @staticmethod
    def _pick_atmosphere(text: str) -> str:
        if any(w in text for w in ["जंगल", "forest", "पेड़", "tree"]):
            return random.choice(["Misty forest", "Dense canopy", "Sunlit clearing"])
        if any(w in text for w in ["मंदिर", "temple", "पूजा", "worship"]):
            return "Tranquil spiritual"
        if any(w in text for w in ["शहर", "city", "urban", "बाजार"]):
            return random.choice(["Urban bustle", "Street life"])
        if any(w in text for w in ["पहाड़", "mountain", "hill"]):
            return random.choice(["Mountain air", "Open sky", "High altitude"])
        if any(w in text for w in ["समुद्र", "ocean", "sea", "पानी", "water"]):
            return random.choice(["Tranquil water", "Coastal breeze"])
        return random.choice(ATMOSPHERES)

    @staticmethod
    def _pick_palette(emotion: str) -> str:
        mapping = {
            "Mystery": "Cool",
            "Wonder": "Warm",
            "Amazement": "Vibrant",
            "Curiosity": "Natural",
            "Reflection": "Muted",
            "Hope": "Golden",
            "Surprise": "High contrast",
            "Calm": "Pastel",
            "Awe": "Vibrant",
            "Nostalgia": "Warm",
            "Tension": "Cool",
        }
        return mapping.get(emotion, "Natural")

    @staticmethod
    def _pick_subjects(text: str) -> list[str]:
        for theme, subjects in FOCUS_THEMES.items():
            if theme in text:
                return subjects
        return FOCUS_THEMES["default"]

    @staticmethod
    def _pick_tempo(emotion: str) -> str:
        if emotion in ("Tension", "Surprise", "Dynamic"):
            return "Dynamic"
        if emotion in ("Calm", "Reflection", "Nostalgia"):
            return "Gentle"
        return random.choice(TEMPOS)
