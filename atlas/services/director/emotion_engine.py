"""Phase 11 — Emotional Engine: enforce dominant emotion per scene."""

from services.director.models import Emotion, SceneBlueprint


class EmotionalEngine:
    EMOTION_TAGS = {
        "Wonder": ["अद्भुत", "सुंदर", "wonder", "beautiful", "amazing", "अद्वितीय"],
        "Mystery": ["रहस्य", "mystery", "अनजान", "unknown", "हैरत", "अनोखा"],
        "Curiosity": ["क्या", "कैसे", "क्यों", "जानते", "पता", "what", "how", "why"],
        "Tension": ["डर", "खतरा", "doubt", "लेकिन", "danger", "चिंता"],
        "Calm": ["शांत", "स्थित", "calm", "peace", "quiet", "धीरे"],
        "Hope": ["उम्मीद", "hope", "विश्वास", "trust", "बेहतर"],
        "Amazement": ["हैरत", "अद्भुत", "अद्वितीय", "amazing", "incredible"],
        "Nostalgia": ["पुराना", "पहले", "old", "past", "याद", "बचपन"],
        "Respect": ["सम्मान", "आस्था", "भक्ति", "परंपरा", "tradition", "संस्कृति"],
        "Reflection": ["सोचो", "think", "विचार", "मौका", "क्या आप"],
    }

    def apply(self, blueprint: SceneBlueprint) -> SceneBlueprint:
        text = f"{blueprint.beat.sentence} {blueprint.beat.visual_goal}"
        lower = text.lower()
        scores: dict[str, int] = {}
        for emotion, tags in self.EMOTION_TAGS.items():
            score = sum(1 for t in tags if t in lower)
            if score > 0:
                scores[emotion] = score

        if scores:
            blueprint.dominant_emotion = max(scores, key=scores.get)
        else:
            blueprint.dominant_emotion = Emotion.CURIOSITY.value

        for shot in blueprint.shots:
            shot.emotion = blueprint.dominant_emotion

        return blueprint
