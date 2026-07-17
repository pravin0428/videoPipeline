"""Phase 1 — Sentence Understanding: split script into story beats with purpose/emotion."""

import re

from services.director.models import Emotion, StoryBeat


class SentenceAnalyzer:
    def analyze(self, script: str) -> list[StoryBeat]:
        sentences = self._split_sentences(script)
        beats = []
        for i, sentence in enumerate(sentences):
            beat = self._classify_beat(sentence, i, len(sentences))
            beats.append(beat)
        return beats

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        parts = re.split(r'(?<=[।?!])\s*', text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _classify_beat(sentence: str, index: int, total: int) -> StoryBeat:
        lower = sentence.lower()
        purpose, emotion = "context", "Curiosity"
        importance = 5

        if index == 0:
            if "?" in sentence or "क्या" in sentence:
                purpose, emotion = "hook", "Mystery"
                importance = 9
            else:
                purpose, emotion = "hook", "Wonder"
                importance = 8
        elif index == total - 1:
            if "?" in sentence:
                purpose, emotion = "close", "Reflection"
                importance = 8
            else:
                purpose, emotion = "close", "Hope"
                importance = 7
        elif any(w in lower for w in ["विश्वास", "मान्यता", "माना", "मानते"]):
            purpose, emotion = "explanation", "Respect"
            importance = 7
        elif any(w in lower for w in ["लेकिन", "हैरत", "अनोखा", "अद्भुत"]):
            purpose, emotion = "reveal", "Amazement"
            importance = 7
        elif any(w in lower for w in ["क्या आप", "जानते हैं", "पता है"]):
            purpose, emotion = "hook", "Curiosity"
            importance = 8
        elif any(w in lower for w in ["स्थित", "गांव", "शहर", "जिला"]):
            purpose, emotion = "context", "Calm"
            importance = 5
        elif any(w in lower for w in ["लाखों", "हजारों", "करोड़ों"]):
            purpose, emotion = "detail", "Amazement"
            importance = 6

        viewer_q = ""
        if purpose == "hook":
            viewer_q = sentence[:60]
        elif "क्यों" in sentence or "कैसे" in sentence:
            viewer_q = sentence[:60]

        visual_goal = ""
        if "गांव" in sentence or "शहर" in sentence:
            visual_goal = "Establish location"
        elif "मंदिर" in sentence:
            visual_goal = "Show architecture and devotion"
        elif "भरोस" in sentence or "विश्वास" in sentence:
            visual_goal = "Visually represent trust and faith"
        elif "प्रकृति" in sentence or "जंगल" in sentence:
            visual_goal = "Capture natural beauty"

        return StoryBeat(
            sentence=sentence,
            purpose=purpose,
            emotion=emotion,
            importance=importance,
            viewer_question=viewer_q,
            visual_goal=visual_goal,
        )
