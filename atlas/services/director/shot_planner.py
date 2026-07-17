"""Phase 3 — Shot Planner: generate shot lists per story beat."""

from services.director.models import (
    CameraMovement, CameraStyle, Emotion, Rhythm, Shot, ShotPurpose,
    StoryBeat, Transition,
)


class ShotPlanner:
    def plan(self, beat: StoryBeat) -> list[Shot]:
        purpose = self._resolve_purpose(beat)
        shots = []

        if purpose in ("hook", "establish"):
            shots.extend(self._opening_shots(beat))
        elif purpose == "explanation":
            shots.extend(self._explanation_shots(beat))
        elif purpose == "reveal":
            shots.extend(self._reveal_shots(beat))
        elif purpose == "detail":
            shots.extend(self._detail_shots(beat))
        elif purpose == "close":
            shots.extend(self._closing_shots(beat))
        else:
            shots.extend(self._default_shots(beat))

        return shots

    @staticmethod
    def _resolve_purpose(beat: StoryBeat) -> str:
        purpose = beat.purpose
        text = beat.sentence.lower()
        if "?" in beat.sentence and "क्या" in beat.sentence:
            return "hook"
        if "स्थित" in text or "गांव" in text:
            return "establish"
        if "मान्यता" in text or "विश्वास" in text or "क्योंकि" in text:
            return "explanation"
        if "अनोखा" in text or "अद्भुत" in text or "हैरत" in text:
            return "reveal"
        if "मौका" in text:
            return "close"
        return purpose

    @staticmethod
    def _opening_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description=f"Wide establishing — {beat.sentence[:40]}",
                camera="Drone", movement="Crane Down",
                duration=4.0, purpose="establish", emotion=beat.emotion,
                transition="Fade In",
            ),
            Shot(
                description=f"Medium — {beat.sentence[:30]}",
                camera="Cinematic", movement="Slow Push",
                duration=3.5, purpose="hook", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description="Intriguing detail that raises curiosity",
                camera="Close-up", movement="Static",
                duration=2.5, purpose="emotion", emotion="Curiosity",
                transition="Cut",
            ),
        ]

    @staticmethod
    def _explanation_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description="Context setting — surrounding environment",
                camera="Wide", movement="Pan Right",
                duration=3.0, purpose="context", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description="Explanation detail supporting narration",
                camera="Close-up", movement="Slow Push",
                duration=4.0, purpose="explanation", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description="Supporting visual for the concept",
                camera="Macro", movement="Static",
                duration=3.0, purpose="detail", emotion=beat.emotion,
                transition="Dissolve",
            ),
        ]

    @staticmethod
    def _reveal_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description="Build-up — approaching the subject",
                camera="Tracking", movement="Track Forward",
                duration=3.0, purpose="transition", emotion="Tension",
                transition="Cut",
            ),
            Shot(
                description="The reveal — main subject in full view",
                camera="Wide", movement="Crane Up",
                duration=4.0, purpose="reveal", emotion="Amazement",
                transition="Cut",
            ),
            Shot(
                description="Impact — reaction or detail of the reveal",
                camera="Close-up", movement="Slow Push",
                duration=3.5, purpose="emotion", emotion="Amazement",
                transition="Cut",
            ),
        ]

    @staticmethod
    def _detail_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description=f"Main subject — {beat.sentence[:30]}",
                camera="Close-up", movement="Slow Push",
                duration=3.0, purpose="detail", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description="Environmental detail supporting the narrative",
                camera="Macro", movement="Static",
                duration=2.5, purpose="detail", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description="Wider context of the detail",
                camera="Wide", movement="Pan Left",
                duration=3.0, purpose="context", emotion=beat.emotion,
                transition="Cut",
            ),
        ]

    @staticmethod
    def _closing_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description="Contemplative wide of the entire subject",
                camera="Drone", movement="Crane Up",
                duration=4.0, purpose="close", emotion="Reflection",
                transition="Dissolve",
            ),
            Shot(
                description="Final intimate moment",
                camera="Close-up", movement="Static",
                duration=3.5, purpose="emotion", emotion=beat.emotion,
                transition="Crossfade",
            ),
            Shot(
                description="Fade to black — lingering final image",
                camera="Wide", movement="Static",
                duration=3.0, purpose="close", emotion="Reflection",
                transition="Fade Out",
            ),
        ]

    @staticmethod
    def _default_shots(beat: StoryBeat) -> list[Shot]:
        return [
            Shot(
                description=f"Establishing — {beat.sentence[:30]}",
                camera="Wide", movement="Static",
                duration=3.0, purpose="context", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description=f"Detail — {beat.sentence[:20]}",
                camera="Close-up", movement="Slow Push",
                duration=3.0, purpose="detail", emotion=beat.emotion,
                transition="Cut",
            ),
            Shot(
                description=f"Supporting view",
                camera="Cinematic", movement="Pan Right",
                duration=2.5, purpose="context", emotion=beat.emotion,
                transition="Cut",
            ),
        ]
