"""V5 DirectorService — the creative brain of Atlas.

Converts a narration script into a complete ProductionPlan (JSON).
The output is model-independent — any video generation backend (Wan, LTX,
Hunyuan, CogVideoX, future OpenAI/Google) can read the same plan.

The renderer is a dumb executor. All creative decisions live here.
"""

import json
import re
from pathlib import Path

from services.director_v5.models import ProductionPlan, ScenePlan, ShotPlan


class DirectorService:
    def __init__(self):
        self._camera_pool = self._build_camera_pool()

    @staticmethod
    def _build_camera_pool() -> list[dict]:
        return [
            {"camera": "Drone", "movement": "Crane Down", "lens": "24mm wide", "purpose": "establish"},
            {"camera": "Drone", "movement": "Crane Up", "lens": "24mm wide", "purpose": "close"},
            {"camera": "Wide", "movement": "Static", "lens": "35mm wide", "purpose": "context"},
            {"camera": "Wide", "movement": "Pan Right", "lens": "35mm wide", "purpose": "context"},
            {"camera": "Wide", "movement": "Pan Left", "lens": "35mm wide", "purpose": "context"},
            {"camera": "Cinematic", "movement": "Slow Push", "lens": "50mm standard", "purpose": "hook"},
            {"camera": "Close-up", "movement": "Slow Push", "lens": "85mm portrait", "purpose": "detail"},
            {"camera": "Close-up", "movement": "Static", "lens": "85mm portrait", "purpose": "emotion"},
            {"camera": "Close-up", "movement": "Tilt Up", "lens": "85mm portrait", "purpose": "reveal"},
            {"camera": "Macro", "movement": "Static", "lens": "100mm macro", "purpose": "detail"},
            {"camera": "Tracking", "movement": "Track Forward", "lens": "50mm standard", "purpose": "transition"},
            {"camera": "Tracking", "movement": "Track Backward", "lens": "50mm standard", "purpose": "reveal"},
            {"camera": "Aerial", "movement": "Static", "lens": "24mm wide", "purpose": "establish"},
            {"camera": "Underground", "movement": "Static", "lens": "16mm wide", "purpose": "detail"},
            {"camera": "POV", "movement": "Handheld", "lens": "35mm wide", "purpose": "emotion"},
            {"camera": "Architecture", "movement": "Tilt Up", "lens": "24mm wide", "purpose": "establish"},
        ]

    def direct(self, title: str, script: str, output_path: str | None = None) -> ProductionPlan:
        sentences = self._split_sentences(script)
        beats = [self._analyze_sentence(s, i, len(sentences)) for i, s in enumerate(sentences)]

        scenes = []
        for i, beat in enumerate(beats):
            scene = self._build_scene(i + 1, beat)
            scenes.append(scene)

        pacing = self._plan_pacing(beats)
        emotional_flow = [b["emotion"] for b in beats]
        total_dur = sum(s.total_duration for s in scenes)

        plan = ProductionPlan(
            title=title,
            total_duration=total_dur,
            scenes=scenes,
            emotional_flow=emotional_flow,
            pacing_structure=pacing,
            music_mood=self._select_music_mood(emotional_flow),
            sound_effects=self._select_sound_effects(emotional_flow),
            viewer_engagement_strategy=self._engagement_strategy(beats),
        )

        if output_path:
            Path(output_path).write_text(plan.to_json(), encoding="utf-8")

        return plan

    def _build_scene(self, number: int, beat: dict) -> ScenePlan:
        shots = self._plan_shots(number, beat)

        purpose = beat["purpose"]
        emotion = beat["emotion"]
        rhythm = beat["rhythm"]
        text = beat["sentence"]

        base_dur = 2.5 if rhythm == "fast" else 4.0
        for shot in shots:
            shot.duration = self._adjust_duration(base_dur, shot.shot_number, rhythm)
            shot.atmosphere = self._select_atmosphere(emotion)
            shot.lighting = self._select_lighting(text)

        media_type = self._recommend_media_type(text)

        stock_prompt = self._build_stock_prompt(text, emotion)
        ai_prompt = self._build_ai_prompt(text, emotion)
        photo_prompt = self._build_photo_prompt(text, emotion)

        scene = ScenePlan(
            scene_number=number,
            narrative=text,
            purpose=purpose,
            emotion=emotion,
            pacing=rhythm,
            visual_goal=beat["visual_goal"],
            shots=shots,
            recommended_media_type=media_type,
            ai_video_prompt=ai_prompt,
            stock_video_prompt=stock_prompt,
            photo_prompt=photo_prompt,
            map_requirements=self._extract_map_reqs(text),
            infographic_requirements=self._extract_infographic_reqs(text),
            scientific_animation_requirements=self._extract_science_reqs(text),
            b_roll_suggestions=self._b_roll(text),
            subtitle_emphasis=self._extract_keywords(text),
        )

        scene.total_duration = sum(s.duration for s in shots)
        return scene

    def _plan_shots(self, scene_number: int, beat: dict) -> list[ShotPlan]:
        purpose = beat["purpose"]
        text = beat["sentence"]
        emotion = beat["emotion"]
        rhythm = beat["rhythm"]

        if purpose == "hook":
            shot_purposes = ["establish", "hook", "emotion"]
        elif purpose == "establish":
            shot_purposes = ["establish", "context", "detail"]
        elif purpose == "explanation":
            shot_purposes = ["context", "detail", "detail"]
        elif purpose == "reveal":
            shot_purposes = ["transition", "reveal", "emotion"]
        elif purpose == "detail":
            shot_purposes = ["detail", "detail", "context"]
        elif purpose == "close":
            shot_purposes = ["emotion", "close", "close"]
        else:
            shot_purposes = ["context", "detail", "emotion"]

        used_cameras = set()
        shots = []
        for j, sp in enumerate(shot_purposes):
            cam = self._select_camera(sp, used_cameras)
            if cam:
                used_cameras.add(cam["camera"])
            else:
                cam = self._camera_pool[0]

            subject, secondary = self._extract_subjects(text, j)

            shots.append(ShotPlan(
                shot_number=j + 1,
                camera_type=cam.get("camera", "Cinematic"),
                camera_movement=cam.get("movement", "Static"),
                lens_style=cam.get("lens", "50mm standard"),
                lighting=self._select_lighting(text),
                subject=subject,
                secondary_subject=secondary,
                atmosphere=self._select_atmosphere(emotion),
                emotion=emotion,
                duration=4.0,
                cinematic_prompt=self._build_ai_prompt(text, emotion),
                negative_prompt="blurry, low quality, watermark, text overlay",
                media_priority=self._media_priority(text, sp),
                transition=self._select_transition(j, sp, purpose),
                visual_description=self._build_visual_desc(text, cam, j),
                shot_purpose=sp,
            ))
        return shots

    def _select_camera(self, purpose: str, used: set) -> dict | None:
        candidates = [c for c in self._camera_pool if c["purpose"] == purpose and c["camera"] not in used]
        if not candidates:
            candidates = [c for c in self._camera_pool if c["purpose"] == purpose]
        if candidates:
            import random
            return random.choice(candidates)
        return None

    @staticmethod
    def _adjust_duration(base: float, shot_num: int, rhythm: str) -> float:
        if rhythm == "fast":
            d = base * 0.7
        elif rhythm == "slow":
            d = base * 1.3
        else:
            d = base
        if shot_num == 1:
            d *= 1.2
        return max(1.5, min(8.0, d))

    @staticmethod
    def _select_lighting(text: str) -> str:
        if "सुबह" in text or "सूरज" in text:
            return "Golden Hour"
        if "रात" in text:
            return "Moonlight"
        if "मंदिर" in text or "दीप" in text:
            return "Warm oil lamp glow"
        if "जंगल" in text or "प्रकृत" in text:
            return "Dappled forest light"
        if "गुफा" in text or "अंधेर" in text:
            return "Dramatic shadow"
        return "Natural documentary lighting"

    @staticmethod
    def _select_atmosphere(emotion: str) -> str:
        return {
            "Mystery": "Misty, atmospheric, slightly dark",
            "Wonder": "Bright, expansive, awe-inspiring",
            "Curiosity": "Inviting, warm, engaging",
            "Calm": "Peaceful, serene, gentle",
            "Tension": "Dramatic, intense, shadowy",
            "Hope": "Warm, uplifting, golden tones",
            "Amazement": "Vibrant, rich, stunning",
            "Reflection": "Contemplative, quiet, intimate",
            "Respect": "Reverent, grand, timeless",
            "Nostalgia": "Warm, soft, slightly faded",
        }.get(emotion, "Natural documentary atmosphere")

    @staticmethod
    def _select_transition(shot_index: int, shot_purpose: str, scene_purpose: str) -> str:
        if shot_index == 0 and scene_purpose == "hook":
            return "Fade In"
        if shot_index == 0:
            return "Cut"
        if shot_purpose == "emotion":
            return "Dissolve"
        if shot_purpose == "reveal":
            return "Match Cut"
        if shot_purpose == "close":
            return "Fade Out"
        return "Cut"

    @staticmethod
    def _recommend_media_type(text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["जड़", "फंगस", "कोशिका", "डीएनए", "गुरुत्व", "कोशिका"]):
            return "scientific_animation"
        if any(w in lower for w in ["जनसंख्या", "प्रतिशत", "लाख", "करोड़"]):
            return "infographic"
        if any(w in lower for w in ["स्थित", "जिला", "नक्शा"]):
            return "map"
        if any(w in lower for w in ["प्राचीन", "इतिहास", "साम्राज्य", "शताब्दी"]):
            return "historical_reconstruction"
        if any(w in lower for w in ["विशाल", "दृश्य", "प्रकृत"]):
            return "stock_video"
        return "stock_video"

    @staticmethod
    def _media_priority(text: str, purpose: str) -> list[str]:
        lower = text.lower()
        if any(w in lower for w in ["जड़", "फंगस", "कोशिका"]):
            return ["scientific_animation", "infographic", "stock_video"]
        if any(w in lower for w in ["जनसंख्या", "प्रतिशत"]):
            return ["infographic", "stock_video", "photo"]
        if any(w in lower for w in ["स्थित", "जिला"]):
            return ["map", "stock_video", "photo"]
        return ["stock_video", "photo"]

    @staticmethod
    def _analyze_sentence(sentence: str, index: int, total: int) -> dict:
        lower = sentence.lower()
        purpose = "context"
        emotion = "Curiosity"
        importance = 5

        if index == 0:
            if "?" in sentence or "क्या" in sentence:
                purpose, emotion = "hook", "Mystery"
                importance = 10
            else:
                purpose, emotion = "hook", "Wonder"
                importance = 9
        elif index == total - 1:
            if "?" in sentence:
                purpose, emotion = "close", "Reflection"
                importance = 9
            else:
                purpose, emotion = "close", "Hope"
                importance = 8
        elif any(w in lower for w in ["विश्वास", "मान्यता", "माना"]):
            purpose, emotion = "explanation", "Respect"
            importance = 7
        elif any(w in lower for w in ["लेकिन", "हैरत", "अनोखा"]):
            purpose, emotion = "reveal", "Amazement"
            importance = 8
        elif any(w in lower for w in ["स्थित", "गांव", "शहर"]):
            purpose, emotion = "establish", "Calm"
            importance = 6
        elif any(w in lower for w in ["लाखों", "हजारों"]):
            purpose, emotion = "detail", "Amazement"
            importance = 7

        visual_map = {
            "hook": "Capture attention immediately with an intriguing visual",
            "establish": "Show the location and context clearly",
            "explanation": "Visually explain the concept",
            "reveal": "Build up then reveal the key visual",
            "detail": "Show specific details up close",
            "close": "Leave the audience with a lasting impression",
        }

        return {
            "sentence": sentence,
            "purpose": purpose,
            "emotion": emotion,
            "importance": importance,
            "rhythm": "fast" if purpose in ("hook", "reveal") else "slow",
            "visual_goal": visual_map.get(purpose, "Support the narration visually"),
        }

    @staticmethod
    def _plan_pacing(beats: list[dict]) -> list[dict]:
        pacing = []
        for i, b in enumerate(beats):
            pos = i / max(len(beats) - 1, 1)
            if pos < 0.15:
                r = "fast"
            elif pos < 0.35:
                r = "fast"
            elif pos < 0.65:
                r = "slow"
            elif pos < 0.85:
                r = "fast"
            else:
                r = "slow"
            pacing.append({"beat": i + 1, "rhythm": r, "purpose": b["purpose"]})
        return pacing

    @staticmethod
    def _extract_subjects(text: str, shot_index: int) -> tuple[str, str]:
        primary_map = [
            "मंदिर", "गांव", "शहर", "मूर्ति", "पेड़", "जंगल", "नदी", "पहाड़",
            "लोग", "दरवाज़ा", "प्रवेश द्वार", "ताला", "घर",
        ]
        secondary_map = [
            "लोग", "श्रद्धालु", "दीप", "घंटी", "फूल", "आकाश", "बादल",
            "प्रकाश", "परिवार", "बच्चे",
        ]
        primary = next((w for w in primary_map if w in text), "the main subject")
        secondary = next((w for w in secondary_map if w in text and w != primary), "surrounding environment")
        return primary, secondary

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        keywords = []
        for w in ["शनि", "ताला", "भरोसा", "मंदिर", "गांव", "आस्था", "परंपरा",
                   "million", "लाख", "करोड़", "प्रतिशत", "वर्ष", "साल"]:
            if w in text:
                keywords.append(w)
        return keywords[:3]

    @staticmethod
    def _extract_map_reqs(text: str) -> dict | None:
        place = re.search(r"([\u0900-\u097F\s]{3,30})\s*(जिला|district|में स्थित|गांव)", text)
        if place:
            return {"location": place.group(1).strip()[:30], "zoom_levels": ["locator", "district", "village"]}
        return None

    @staticmethod
    def _extract_infographic_reqs(text: str) -> list[dict] | None:
        patterns = [
            (r"(\d+[.,]?\d*)\s*(लाख|करोड़|million|billion)", "population"),
            (r"(\d+)\s*(प्रतिशत|percent)", "percentage"),
            (r"(\d+)\s*(किमी|km|मीटर|meter|फीट|feet)", "measurement"),
            (r"(\d{3,4})\s*(ईसा|ई\.|बीसी|AD|BC)", "date"),
        ]
        results = []
        for pattern, dtype in patterns:
            m = re.search(pattern, text)
            if m:
                results.append({"value": m.group(1), "type": dtype})
        return results if results else None

    @staticmethod
    def _extract_science_reqs(text: str) -> dict | None:
        concepts = [
            ("root", ["जड़", "root", "roots", "underground"]),
            ("fungus", ["फंगस", "fungus", "fungi", "mycorrhizal"]),
            ("network", ["नेटवर्क", "network", "web", "जाल"]),
            ("cell", ["कोशिका", "cell", "cellular"]),
            ("volcano", ["ज्वालामुखी", "volcano", "volcanic"]),
            ("gravity", ["गुरुत्वाकर्षण", "gravity"]),
            ("dna", ["डीएनए", "DNA", "genetic"]),
            ("solar", ["सौर", "solar system", "ग्रह", "planet"]),
        ]
        lower = text.lower()
        for concept, keywords in concepts:
            if any(k in lower for k in keywords):
                return {"concept": concept, "animation_type": "scientific"}
        return None

    @staticmethod
    def _b_roll(text: str) -> list[str]:
        lower = text.lower()
        if "मंदिर" in lower:
            return ["temple bell close-up", "oil lamp flame", "stone carving detail", "incense smoke"]
        if "गांव" in lower:
            return ["village road wide", "house entrance", "village landscape", "sky pan"]
        if "लोग" in lower or "श्रद्धालु" in lower:
            return ["crowd walking medium", "hands folded close-up", "faces portrait", "devotion wide"]
        if "जंगल" in lower or "प्रकृत" in lower:
            return ["leaves macro", "sunlight dappled", "bird on branch", "forest wide"]
        return ["establishing wide", "detail close-up", "context medium"]

    @staticmethod
    def _build_ai_prompt(text: str, emotion: str) -> str:
        tone = emotion.lower()
        return (
            f"Cinematic documentary shot. {text[:60]}. "
            f"{tone} atmosphere, photorealistic, 1080x1920 portrait, "
            f"smooth motion, professional lighting, National Geographic style."
        )

    @staticmethod
    def _build_stock_prompt(text: str, emotion: str) -> str:
        words = text.split()[:6]
        return " ".join(words)

    @staticmethod
    def _build_photo_prompt(text: str, emotion: str) -> str:
        words = text.split()[:4]
        return " ".join(words)

    @staticmethod
    def _build_visual_desc(text: str, camera: dict, shot_index: int) -> str:
        cam_type = camera.get("camera", "Cinematic")
        movement = camera.get("movement", "Static")
        return f"{cam_type} shot, {movement.lower()}. {text[:40]}"

    @staticmethod
    def _select_music_mood(emotions: list[str]) -> str:
        if "Mystery" in emotions or "Tension" in emotions:
            return "Mysterious ambient with subtle tension"
        if "Wonder" in emotions or "Amazement" in emotions:
            return "Cinematic orchestral, awe-inspiring"
        if "Calm" in emotions or "Reflection" in emotions:
            return "Gentle piano and strings, contemplative"
        if "Respect" in emotions:
            return "Traditional orchestral, reverent"
        return "Cinematic documentary score, neutral emotional"

    @staticmethod
    def _select_sound_effects(emotions: list[str]) -> list[str]:
        effects = ["ambient background"]
        if "Tension" in emotions:
            effects.append("subtle drum pulse")
        if "Calm" in emotions:
            effects.append("nature ambience")
        if "Mystery" in emotions:
            effects.append("low frequency drone")
        return effects

    @staticmethod
    def _engagement_strategy(beats: list[dict]) -> str:
        purposes = [b["purpose"] for b in beats]
        strategy = []
        if "hook" in purposes:
            strategy.append("Open with a question or intriguing statement")
        if "reveal" in purposes:
            strategy.append("Build curiosity then deliver the reveal")
        if "close" in purposes:
            strategy.append("End with a reflective question to the viewer")
        if "explanation" in purposes:
            strategy.append("Use clear visual explanations for complex concepts")
        return ". ".join(strategy)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r'(?<=[।?!\n])\s*', text)
        return [p.strip() for p in parts if p.strip()]

    def plan_to_file(self, plan: ProductionPlan, path: str):
        Path(path).write_text(plan.to_json(), encoding="utf-8")
