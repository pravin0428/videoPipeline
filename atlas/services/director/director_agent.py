"""Phase 2 — Director Agent: the editorial brain of Atlas.

Makes all creative decisions:
- Which shots to use
- What order
- Emotional arc
- Pacing
- Visual descriptions
- B-roll needs
"""

import re

from services.director.models import (
    CameraStyle, DocumentaryPacing, Emotion, MediaType, SceneBlueprint,
    Shot, StoryBeat, VisualIntent,
)
from services.director.sentence_analyzer import SentenceAnalyzer
from services.director.shot_planner import ShotPlanner
from services.director.visual_intent import VisualIntentPlanner
from services.director.rhythm import DocumentaryRhythm
from services.director.emotion_engine import EmotionalEngine
from services.director.b_roll import BRollGenerator


class DirectorAgent:
    def __init__(self):
        self.sentence_analyzer = SentenceAnalyzer()
        self.shot_planner = ShotPlanner()
        self.visual_intent = VisualIntentPlanner()
        self.rhythm = DocumentaryRhythm()
        self.emotion_engine = EmotionalEngine()
        self.b_roll = BRollGenerator()

    def direct(self, script: str) -> tuple[list[SceneBlueprint], DocumentaryPacing]:
        beats = self.sentence_analyzer.analyze(script)
        pacing = self.rhythm.plan(beats)

        blueprints = []
        for i, beat in enumerate(beats):
            rhythm = pacing.rhythm_map.get(i, "steady")
            blueprint = self._direct_beat(beat, rhythm)
            blueprints.append(blueprint)

        return blueprints, pacing

    def _direct_beat(self, beat: StoryBeat, rhythm: str) -> SceneBlueprint:
        intent = self.visual_intent.plan(beat)
        shots = self.shot_planner.plan(beat)

        for shot in shots:
            shot.duration = self._adjust_duration(shot.duration, rhythm, beat.importance)

        b_roll_needs = self.b_roll.generate(beat)

        blueprint = SceneBlueprint(
            beat=beat,
            shots=shots,
            visual_intent=intent,
            rhythm=rhythm,
            total_duration=sum(s.duration for s in shots),
            b_roll_needs=b_roll_needs,
        )

        blueprint = self.emotion_engine.apply(blueprint)

        self._plan_asset_types(blueprint)

        return blueprint

    @staticmethod
    def _adjust_duration(base: float, rhythm: str, importance: int) -> float:
        if rhythm == "fast":
            return max(1.5, base * 0.7)
        elif rhythm == "slow":
            return min(6.0, base * 1.3)
        if importance >= 8:
            return base * 1.2
        return base

    @staticmethod
    def _plan_asset_types(blueprint: SceneBlueprint) -> None:
        text = blueprint.beat.sentence.lower()
        for i, shot in enumerate(blueprint.shots):
            if any(w in text for w in ["जड़", "फंगस", "कोशिका", "डीएनए", "गुरुत्व"]):
                shot.media_type = "scientific_animation"
            elif any(w in text for w in ["जनसंख्या", "प्रतिशत", "लाख", "करोड़", "प्रतिशत"]):
                if shot.purpose == "detail":
                    shot.media_type = "infographic"
            elif any(w in text for w in ["प्राचीन", "इतिहास", "साम्राज्य", "शताब्दी"]):
                shot.media_type = "historical_reconstruction"

            only_first_shot = i == 0
            has_location_ref = any(w in text for w in ["स्थित", "जिला", "नक्शा"])
            if has_location_ref and only_first_shot and shot.camera == "Drone":
                shot.media_type = "map"

    @staticmethod
    def to_viewer_report(blueprints: list[SceneBlueprint]) -> list[dict]:
        return [
            {
                "sentence": b.beat.sentence[:60],
                "emotion": b.dominant_emotion,
                "rhythm": b.rhythm,
                "shots": len(b.shots),
                "duration": round(b.total_duration, 1),
                "b_roll": len(b.b_roll_needs),
                "intent": b.visual_intent.scene_description[:50] if b.visual_intent else "",
            }
            for b in blueprints
        ]
