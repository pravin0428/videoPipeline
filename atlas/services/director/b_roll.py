"""Phase 8 — B-Roll Generator: supporting shots for narration."""

from services.director.models import StoryBeat


class BRollGenerator:
    def generate(self, beat: StoryBeat) -> list[str]:
        text = beat.sentence.lower()
        needs = []

        if "मंदिर" in text:
            needs.extend(["temple bell", "oil lamp", "stone carving", "incense smoke", "devotee hands"])
        elif "गांव" in text:
            needs.extend(["village road", "house entrance", "village well", "farm field", "skyline"])
        elif "लोग" in text or "श्रद्धालु" in text:
            needs.extend(["crowd walking", "people praying", "hands folded", "portrait smile"])
        elif "प्रकृत" in text or "जंगल" in text:
            needs.extend(["leaves in wind", "sunlight through trees", "bird flying", "water stream"])
        elif "नदी" in text:
            needs.extend(["river flow", "water reflection", "boat", "bank view"])
        elif "पहाड़" in text:
            needs.extend(["mountain peak", "clouds", "valley view", "hiking trail"])
        else:
            needs.extend(["establishing wide", "detail close-up", "context medium"])

        return needs[:4]

    def for_shot(self, description: str, shot_emotion: str) -> list[str]:
        desc_lower = description.lower()
        if "temple" in desc_lower or "architecture" in desc_lower:
            return ["stone texture", "carving detail", "pillar shot"]
        if "people" in desc_lower or "crowd" in desc_lower:
            return ["faces close-up", "hands gesture", "movement wide"]
        if "nature" in desc_lower or "forest" in desc_lower:
            return ["leaf macro", "insect detail", "light play"]
        return ["wide context", "detail close-up"]
