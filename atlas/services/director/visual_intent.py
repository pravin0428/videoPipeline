"""Phase 4 — Visual Intent Planner: generate visual descriptions not keywords."""

import re

from services.director.models import StoryBeat, VisualIntent


class VisualIntentPlanner:
    def plan(self, beat: StoryBeat) -> VisualIntent:
        text = beat.sentence
        lower = text.lower()

        scene_desc = self._build_description(text, beat.visual_goal)

        primary = self._extract_primary(text)

        secondary = self._extract_secondary(text)

        bg = self._extract_background(text)

        lighting = self._extract_lighting(text)

        color = self._extract_palette(text)

        atmosphere = self._extract_atmosphere(text, beat.emotion)

        camera = self._extract_camera_instruction(text)

        return VisualIntent(
            scene_description=scene_desc,
            primary_subject=primary,
            secondary_subject=secondary,
            background=bg,
            lighting=lighting,
            color_palette=color,
            atmosphere=atmosphere,
            camera_instructions=camera,
            reference_style="Cinematic documentary, National Geographic style",
        )

    @staticmethod
    def _build_description(text: str, goal: str) -> str:
        place_match = re.search(r"(गांव|शहर|जिला|मंदिर)\s*(?:का|के|में)?\s*([\u0900-\u097F\s]{2,20})", text)
        place = place_match.group(0) if place_match else ""
        desc = f"Professional documentary shot. {goal}. {place}. Cinematic composition, rich details."
        return desc

    @staticmethod
    def _extract_primary(text: str) -> str:
        for word in ["मंदिर", "गांव", "शहर", "मूर्ति", "पेड़", "जंगल", "नदी", "पहाड़"]:
            if word in text:
                return word
        return "the main subject"

    @staticmethod
    def _extract_secondary(text: str) -> str:
        for word in ["लोग", "श्रद्धालु", "दीप", "घंटी", "फूल", "दरवाज़ा", "ताला"]:
            if word in text:
                return word
        return "surrounding environment"

    @staticmethod
    def _extract_background(text: str) -> str:
        if "गांव" in text or "शहर" in text:
            return "Village landscape, traditional houses, rural setting"
        if "मंदिर" in text:
            return "Temple architecture, stone walls, ancient structure"
        if "जंगल" in text or "प्रकृत" in text:
            return "Dense forest, natural landscape"
        return "Documentary background setting"

    @staticmethod
    def _extract_lighting(text: str) -> str:
        lower = text.lower()
        if "सुबह" in lower or "सूरज" in lower:
            return "Golden Hour"
        if "रात" in lower:
            return "Moonlight"
        if "मंदिर" in text:
            return "Warm oil lamp glow"
        if "जंगल" in text:
            return "Dappled forest light"
        return "Natural documentary lighting"

    @staticmethod
    def _extract_palette(text: str) -> str:
        if "मंदिर" in text:
            return "Warm golds, oranges, stone browns"
        if "गांव" in text:
            return "Earthy browns, greens, sky blues"
        if "जंगल" in text:
            return "Deep greens, earthy browns"
        if "रात" in text:
            return "Deep blues, blacks, warm light accents"
        return "Warm documentary tones"

    @staticmethod
    def _extract_atmosphere(text: str, emotion: str) -> str:
        atmosphere_map = {
            "Mystery": "Misty, atmospheric, slightly dark",
            "Wonder": "Bright, expansive, awe-inspiring",
            "Curiosity": "Inviting, warm, engaging",
            "Calm": "Peaceful, serene, gentle",
            "Tension": "Dramatic, intense, shadowy",
            "Hope": "Warm, uplifting, golden",
            "Reflection": "Contemplative, quiet, intimate",
        }
        return atmosphere_map.get(emotion, "Natural documentary atmosphere")

    @staticmethod
    def _extract_camera_instruction(text: str) -> str:
        if "विशाल" in text or "बड़ा" in text or "पूरा" in text:
            return "Wide shot to capture scale. Slow push."
        if "छोटा" in text or "सूक्ष्म" in text:
            return "Close-up. Macro details."
        if "मंदिर" in text:
            return "Low angle looking up at architecture. Slow tilt up."
        if "लोग" in text or "भक्त" in text or "श्रद्धालु" in text:
            return "Medium shot of people. Warm intimate composition."
        return "Cinematic establishing shot. Smooth gimbal movement."
